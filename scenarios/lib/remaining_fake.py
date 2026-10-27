"""Synthetic signed-grant transport; this models bounds and never claims AWS SigV4 proof."""
import io, os, secrets, time
class NoSuchKey(Exception): pass
class S3:
    class exceptions: NoSuchKey = NoSuchKey
    def __init__(self): self.objects = {}; self.grants = {}; self.offset = 0
    def now(self): return time.time() + self.offset
    def generate_presigned_url(self, operation, *, Params, ExpiresIn, HttpMethod):
        assert operation == "put_object" and HttpMethod == "PUT" and 1 <= ExpiresIn <= 900
        token=secrets.token_hex(16); self.grants[token]=(Params["Bucket"],Params["Key"],Params["ContentType"],Params["ContentLength"],self.now()+ExpiresIn)
        return os.environ['UPLOAD_ENDPOINT'] + "/s3/" + Params["Key"] + "?token=" + token
    def put_object(self, **kwargs): self.objects[(kwargs["Bucket"], kwargs["Key"])] = dict(kwargs); return {}
    def get_object(self, **kwargs):
        try: obj=self.objects[(kwargs["Bucket"], kwargs["Key"])]
        except KeyError: raise NoSuchKey()
        return {"Body":io.BytesIO(obj['Body']), "ContentType": obj['ContentType']}
class Boto3:
    def __init__(self): self.s3 = S3()
    def client(self, service, **kwargs): assert service == "s3"; return self.s3
