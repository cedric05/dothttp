import enum
import os
from dataclasses import dataclass, field
from typing import List, Optional, Union

from dothttp import DotHttpException


@dataclass
class Allhttp:
    pass


@dataclass
class NameWrap:
    name: str
    base: Optional[str] = None


@dataclass
class UrlWrap:
    method: str
    url: str


@dataclass
class BasicAuth:
    username: str
    password: str


@dataclass
class DigestAuth:
    username: str
    password: str

@dataclass
class HawkAuth:
    hawk_id: str
    key: str
    algorithm: Optional[str] = None


@dataclass
class AwsAuthWrap:
    access_id: str
    secret_token: str
    service: str
    region: Union[str, None]

@dataclass
class NtlmAuthWrap:
    username: str
    password: str


@dataclass
class AuthWrap:
    digest_auth: Optional[DigestAuth] = None
    basic_auth: Optional[BasicAuth] = None
    aws_auth: Optional[AwsAuthWrap] = None
    ntlm_auth: Optional[NtlmAuthWrap] = None
    hawk_auth: Optional[HawkAuth] = None

@dataclass
class Query:
    key: str
    value: str


@dataclass
class Header:
    key: str
    value: str


@dataclass
class Line:
    header: Optional[Header]
    query: Optional[Query]


@dataclass
class MultiPartFile:
    name: str
    path: str
    type: Optional[str] = None


@dataclass
class FilesWrap:
    files: List[MultiPartFile]


@dataclass
class TripleOrDouble:
    triple: Optional[str] = None
    str: Optional[str] = None


@dataclass
class Payload:
    data: Optional[List[TripleOrDouble]]
    datajson: Optional[dict]
    file: Optional[str]
    json: Optional[dict]
    fileswrap: Optional[FilesWrap]
    type: Optional[str]


@dataclass
class ToFile:
    output: str

@dataclass
class LangOption:
    javascript: Optional[str]
    python: Optional[str]

@dataclass
class TestScript:
    script: Optional[str]
    lang: Optional[LangOption] = field(init=False)


@dataclass
class Certificate:
    cert: str
    key: Optional[str]


@dataclass
class P12Certificate:
    p12_file: Optional[str] = None
    password: Optional[str] = None


@dataclass
class ExtraArg:
    # clears session after each
    clear: Optional[str] = ''
    # allows insecure
    insecure: Optional[str] = ''


@dataclass
class Http:
    namewrap: Optional[NameWrap]
    urlwrap: UrlWrap
    authwrap: Optional[AuthWrap]
    certificate: Optional[Union[Certificate, P12Certificate]]
    lines: Optional[List[Line]]
    payload: Optional[Payload]
    output: Optional[ToFile]
    description: Optional[str] = None
    extra_args: Optional[List[ExtraArg]] = field(default_factory=lambda: [])
    script_wrap: Optional[TestScript] = field(default_factory=lambda: TestScript(''))


@dataclass
class Allhttp:
    allhttps: List[Http]


# one can get list of services and regions from
# https://api.regional-table.region-services.aws.a2z.com/index.json


# this is a static list
# although there are dynamic was to retrieve this
# we choose not to.
AWS_REGION_LIST = {"us-east-2",
                   "us-east-1",
                   "us-west-1",
                   "us-west-2",
                   "af-south-1",
                   "ap-east-1",
                   "ap-south-1",
                   "ap-northeast-3",
                   "ap-northeast-2",
                   "ap-southeast-1",
                   "ap-southeast-2",
                   "ap-northeast-1",
                   "ca-central-1",
                   "cn-north-1",
                   "cn-northwest-1",
                   "eu-central-1",
                   "eu-west-1",
                   "eu-west-2",
                   "eu-south-1",
                   "eu-west-3",
                   "eu-north-1",
                   "me-south-1",
                   "sa-east-1",
                   }

AWS_SERVICES_LIST = {'acm',
                     'aiq',
                     'alexaforbusiness',
                     'amazonlocationservice',
                     'amplify',
                     'apigateway',
                     'appflow',
                     'application-autoscaling',
                     'appmesh',
                     'appstream',
                     'appsync',
                     'artifact',
                     'athena',
                     'auditmanager',
                     'augmentedairuntime',
                     'aurora',
                     'backup',
                     'batch',
                     'braket',
                     'budgets',
                     'chatbot',
                     'chime',
                     'cloud9',
                     'clouddirectory',
                     'cloudenduredisasterrecovery',
                     'cloudenduremigration',
                     'cloudformation',
                     'cloudfront',
                     'cloudhsmv2',
                     'cloudsearch',
                     'cloudshell',
                     'cloudtrail',
                     'cloudwatch',
                     'codeartifact',
                     'codebuild',
                     'codecommit',
                     'codedeploy',
                     'codeguruprofiler',
                     'codepipeline',
                     'codestar',
                     'cognito-identity',
                     'comprehend',
                     'comprehendmedical',
                     'compute-optimizer',
                     'config',
                     'connect',
                     'controltower',
                     'costexplorer',
                     'cur',
                     'dataexchange',
                     'datapipeline',
                     'datasync',
                     'deepcomposer',
                     'deeplens',
                     'deepracer',
                     'detective',
                     'devicefarm',
                     'devops-guru',
                     'directconnect',
                     'discovery',
                     'dms',
                     'docdb',
                     'ds',
                     'dynamodb',
                     'ebs',
                     'ec2',
                     'ecr',
                     'ecs',
                     'efs',
                     'eks',
                     'elastic-inference',
                     'elasticache',
                     'elasticbeanstalk',
                     'elastictranscoder',
                     'elb',
                     'emr',
                     'es',
                     'eventbridge',
                     'fargate',
                     'firehose',
                     'fis',
                     'fms',
                     'forecast',
                     'frauddetector',
                     'freertosota',
                     'fsx-lustre',
                     'fsx-windows',
                     'gamelift',
                     'globalaccelerator',
                     'glue',
                     'greengrass',
                     'groundstation',
                     'guardduty',
                     'honeycode',
                     'iam',
                     'inspector',
                     'iot',
                     'iot1click-projects',
                     'iotanalytics',
                     'iotdevicedefender',
                     'iotdevicemanagement',
                     'iotevents-data',
                     'iotsitewise',
                     'iotthingsgraph',
                     'ivs',
                     'kafka',
                     'kendra',
                     'kinesis',
                     'kinesisanalytics',
                     'kinesisvideo',
                     'kms',
                     'lakeformation',
                     'lambda',
                     'lex-runtime',
                     'license-manager',
                     'lightsail',
                     'lookoutvision',
                     'lumberyard',
                     'macie',
                     'managedblockchain',
                     'managedservices',
                     'marketplace',
                     'mcs',
                     'mediaconnect',
                     'mediaconvert',
                     'medialive',
                     'mediapackage',
                     'mediastore',
                     'mediatailor',
                     'mgh',
                     'mgn',
                     'mq',
                     'mwaa',
                     'neptune',
                     'network-firewall',
                     'nimble',
                     'opsworks',
                     'opsworkschefautomate',
                     'opsworkspuppetenterprise',
                     'organizations',
                     'outposts',
                     'personalize',
                     'phd',
                     'pinpoint',
                     'polly',
                     'privatelink',
                     'proton',
                     'qldb',
                     'quicksight',
                     'ram',
                     'rds',
                     'rdsvmware',
                     'redshift',
                     'rekognition',
                     'robomaker',
                     'route53',
                     's3',
                     'sagemaker',
                     'secretsmanager',
                     'securityhub',
                     'serverlessrepo',
                     'servicecatalog',
                     'servicediscovery',
                     'ses',
                     'shield',
                     'sms',
                     'snowball',
                     'snowcone',
                     'snowmobile',
                     'sns',
                     'sqs',
                     'ssm',
                     'sso',
                     'stepfunctions',
                     'storagegateway',
                     'sumerian',
                     'support',
                     'swf',
                     'textract',
                     'timestream',
                     'transcribe',
                     'transcribemedical',
                     'transfer',
                     'transitgateway',
                     'translate',
                     'trustedadvisor',
                     'vmwarecloudonaws',
                     'vpc',
                     'vpn',
                     'waf',
                     'wam',
                     'wellarchitectedtool',
                     'workdocs',
                     'worklink',
                     'workmail',
                     'workspaces',
                     'xray'}


class HttpFileType(enum.Enum):
    Notebookfile = ("notebook", ("hnbk", "httpbook"))
    Httpfile = ("http", ('http', 'dhttp'))

    def __init__(self, typename, filetypes):
        self.file_exts = filetypes
        self.file_type = typename

    @staticmethod
    def get_from_filetype(filetype: str):
        if filetype == HttpFileType.Notebookfile.file_type:
            return HttpFileType.Notebookfile
        return HttpFileType.Httpfile

    @staticmethod
    def get_format_from_file_name(filename: str):
        _, ext = os.path.splitext(filename)
        if ext and len(ext) > 0:
            ext = ext[1:]
        if ext in HttpFileType.Notebookfile.file_exts:
            return HttpFileType.Notebookfile
        elif ext in HttpFileType.Httpfile.file_exts:
            return HttpFileType.Httpfile
        raise DotHttpException("unknown file type")



class ScriptType(enum.Enum):
    PYTHON = "python"
    JAVA_SCRIPT = "javascript"

    @staticmethod
    def get_script_type(script_type: LangOption):
        if script_type == "python":
            return ScriptType.PYTHON
        else:
            return ScriptType.JAVA_SCRIPT
