from injector import singleton
from pydantic_settings import BaseSettings


@singleton
class EnvironmentInterface(BaseSettings):
    pass
