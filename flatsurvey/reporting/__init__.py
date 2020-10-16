from .report import Report

from .log import Log, log
from .yaml import Yaml, yaml
from .dynamodb import DynamoDB, dynamodb

commands = [log, yaml, dynamodb]
