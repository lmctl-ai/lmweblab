"""Small DynamoDB transport double for scenarios 07–09; no credentials or network."""
import copy
import threading

class ConditionalCheckFailedException(Exception):
    response = {"Error": {"Code": "ConditionalCheckFailedException"}}

class Table:
    def __init__(self): self.rows = {}; self.lock = threading.RLock()
    def put_item(self, *, Item, ConditionExpression=None):
        with self.lock:
            assert isinstance(Item.get('pk'), str)
            assert ConditionExpression in (None, 'attribute_not_exists(pk)')
            if ConditionExpression and Item['pk'] in self.rows: raise ConditionalCheckFailedException()
            self.rows[Item['pk']] = copy.deepcopy(Item)
            return {}
    def get_item(self, *, Key, **kwargs):
        with self.lock:
            return {'Item': copy.deepcopy(self.rows[Key['pk']])} if Key.get('pk') in self.rows else {}
    def delete_item(self, *, Key):
        with self.lock: self.rows.pop(Key.get('pk'), None); return {}
    def update_item(self, *, Key, UpdateExpression, ExpressionAttributeValues, ReturnValues, ConditionExpression=None):
        with self.lock:
            assert UpdateExpression == 'SET hits = if_not_exists(hits, :zero) + :one'
            assert ReturnValues == 'ALL_NEW'
            assert ConditionExpression in (None, 'attribute_exists(pk)')
            if ConditionExpression and Key['pk'] not in self.rows: raise ConditionalCheckFailedException()
            row = self.rows.setdefault(Key['pk'], {'pk': Key['pk']})
            row['hits'] = row.get('hits', ExpressionAttributeValues[':zero']) + ExpressionAttributeValues[':one']
            return {'Attributes': copy.deepcopy(row)}

class Boto3:
    def __init__(self): self.tables = {}
    def resource(self, service): assert service == 'dynamodb'; return self
    def Table(self, name): return self.tables.setdefault(name, Table())
    def client(self, service): raise AssertionError('unexpected fixture service: '+service)
