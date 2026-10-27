"""Explicit offline fixtures for the deployed handlers; no credential or network code."""
import copy
import io

class Table:
    def __init__(self): self.rows={}; self.counter=0
    def put_item(self,*,Item):
        assert isinstance(Item.get('pk'),str), 'table requires a string pk'
        self.rows[Item['pk']]=copy.deepcopy(Item);return {}
    def get_item(self,**kwargs):
        item=self.rows.get(kwargs["Key"]["pk"]);return {"Item":copy.deepcopy(item)} if item else {}
    def update_item(self,**kwargs):
        assert kwargs['Key']=={'pk':'counter'} and kwargs['ReturnValues']=='UPDATED_NEW'
        self.counter+=1;return {'Attributes':{'runs':self.counter}}
    def scan(self,*,Limit,**kwargs):
        rows=list(self.rows.values());start=kwargs.get('ExclusiveStartKey',{}).get('pk')
        offset=next((i+1 for i,row in enumerate(rows) if row['pk']==start),0)
        page=rows[offset:offset+Limit];out={'Items':copy.deepcopy(page)}
        if page and offset+Limit<len(rows):out['LastEvaluatedKey']={'pk':page[-1]['pk']}
        return out

class MissingObject(Exception):
    def __init__(self):self.response={"Error":{"Code":"NoSuchKey"}}

class S3:
    def __init__(self):self.objects={}
    def put_object(self,**kwargs):self.objects[(kwargs['Bucket'],kwargs['Key'])]=copy.deepcopy(kwargs);return {}
    def get_object(self,**kwargs):
        item=self.objects.get((kwargs['Bucket'],kwargs['Key']))
        if item is None:raise MissingObject()
        return {"Body":io.BytesIO(item['Body'])}

class Boto3:
    def __init__(self):self.tables={};self.s3=S3()
    def resource(self,service):
        assert service=='dynamodb';return self
    def Table(self,name):return self.tables.setdefault(name,Table())
    def client(self,service):
        assert service=='s3';return self.s3
