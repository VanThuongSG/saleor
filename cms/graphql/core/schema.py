import graphene

from .mutations import FileUpload
from .types import NonNullList


class CoreQueries(graphene.ObjectType):
    pass


class CoreMutations(graphene.ObjectType):
    file_upload = FileUpload.Field()
