import abc
import cppyy
import dataclasses
from typing import Dict, Self

def ConstructCppyyType(typename: str) -> object:
    type = getattr(cppyy.gbl, typename)
    new = type.__new__(type)
    type.__init__(new)
    return new

@dataclasses.dataclass
class CppyyTypeHint():
    members_to_serialize: list[str] = dataclasses.field(default_factory=lambda: ([]))

@dataclasses.dataclass
class CppyySerializeObject():
    object: object
    type: type
    typename: str

    def __eq__(self: Self, __o: object) -> bool:
        if isinstance(__o, CppyySerializeObject):
            return self.type == __o.type or self.typename == __o.typename
        if isinstance(__o, str):
            return self.typename == __o
        return False

    def __str__(self: Self) -> str:
        return self.typename

    @classmethod
    def from_object(cls, object: object) -> Self:
        object_type = type(object)
        return CppyySerializeObject(
            object=object,
            type=object_type,
            typename=object_type.__name__,
        )

@dataclasses.dataclass
class CppyyContext():
    output: CppyySerializeObject
    input: CppyySerializeObject
    member: str
    serializer: object

class CppyyTypeHandler(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def typename(cls) -> str:
        raise NotImplemented()
    
    @classmethod
    @abc.abstractmethod
    def serialize(cls, context: CppyyContext):
        raise NotImplemented()
    
    @classmethod
    @abc.abstractmethod
    def deserialize(cls, context: CppyyContext):
        raise NotImplemented()
    
    def __eq__(self, other: object) -> bool:
        return self.typename() == other

class PrimitiveTypeHandler(CppyyTypeHandler):
    @classmethod
    def serialize(cls, context: CppyyContext):
        context.output.object = context.input.object

    @classmethod
    def deserialize(cls, context: CppyyContext):
        context.output.object = context.input.object

class StringHandler(PrimitiveTypeHandler):
    @classmethod
    def typename(cls) -> str:
        return "str"
    
class IntegerHandler(PrimitiveTypeHandler):
    @classmethod
    def typename(cls) -> str:
        return "int"
    
class BooleanHandler(PrimitiveTypeHandler):
    @classmethod
    def typename(cls) -> str:
        return "bool"
    
class FloatHandler(PrimitiveTypeHandler):
    @classmethod
    def typename(cls) -> str:
        return "float"

class VectorHandler(CppyyTypeHandler):
    @classmethod
    def typename(cls) -> str:
        return "vector<T>"
    
    @classmethod
    def serialize(cls, context: CppyyContext):
        context.output.object = []
        for data in context.input.object:
            context.output.object.append(context.serializer.serialize(data))

    @classmethod
    def deserialize(cls, context: CppyyContext):
        for data in context.input.object:
            new = ConstructCppyyType(context.output.object.value_type)
            context.serializer.deserialize(new, data)
            context.output.object.push_back(new)
    
    def __eq__(self, other: object):
        return (other[:7] == "vector<" and other[-1:] == ">")

class CppyyMethods(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def determinant(cls, context: CppyyContext) -> CppyySerializeObject:
        raise NotImplemented()
    
    @classmethod
    @abc.abstractmethod
    def auto(cls, context: CppyyContext):
        raise NotImplemented()
    
    @classmethod
    @abc.abstractmethod
    def member(cls, context: CppyyContext):
        raise NotImplemented()

    @classmethod
    @abc.abstractmethod
    def handler(cls, context: CppyyContext, handler: CppyyTypeHandler):
        raise NotImplemented()

class CppyySerializeMethods(CppyyMethods):
    @classmethod
    def determinant(cls, context: CppyyContext) -> CppyySerializeObject:
        return context.input

    @classmethod
    def auto(cls, context: CppyyContext):
        data = getattr(context.input.object, context.member)
        if not callable(data):
            context.output.object[context.member] = context.serializer.serialize(data)

    @classmethod
    def member(cls, context: CppyyContext):
        assert(hasattr(context.input.object, context.member))
        context.output.object[context.member] = context.serializer.serialize(getattr(context.input.object, context.member))

    @classmethod
    @abc.abstractmethod
    def handler(cls, context: CppyyContext, handler: CppyyTypeHandler):
        handler.serialize(context)

class CppyyDeserializeMethods(CppyyMethods):
    @classmethod
    def determinant(cls, context: CppyyContext) -> CppyySerializeObject:
        return context.output
    
    @classmethod
    def auto(cls, context: CppyyContext):
        data = getattr(context.output.object, context.member)
        if not callable(data) and context.member in context.input.object:
            context.serializer.deserialize(data, context.input.object[context.member])

    @classmethod
    def member(cls, context: CppyyContext):
        assert(hasattr(context.output.object, context.member))
        setattr(context.output.object, context.member, context.serializer.deserialize(getattr(context.output.object, context.member), context.input.object[context.member]))

    @classmethod
    @abc.abstractmethod
    def handler(cls, context: CppyyContext, handler: CppyyTypeHandler):
        handler.deserialize(context)

class CppyySerializer():
    PrimitiveTypes = [
    ]
    DefaultHandlers = [
        StringHandler(),
        IntegerHandler(),
        BooleanHandler(),
        FloatHandler(),
        VectorHandler()
    ]
    SerializeMethods = CppyySerializeMethods
    DeserializeMethods = CppyyDeserializeMethods

    def __init__(self, hints: Dict[str, CppyyTypeHint] = {}, handlers: list[CppyyTypeHandler] = DefaultHandlers):
        self.__hints = hints
        self.__handlers = handlers
        self.__recursion = 0

        for _, hint in hints.items():
            assert isinstance(hint, CppyyTypeHint)
        
        for handler in handlers:
            assert issubclass(type(handler), CppyyTypeHandler)

    def serialize(self, data: object) -> object:
        output = {}
        return self.__process__(self.__get_context__(output, data, None, self), self.SerializeMethods)

    def deserialize(self, object: object, data: object) -> object:
        return self.__process__(self.__get_context__(object, data, None, self), self.DeserializeMethods)
    
    def __process__(self, context: CppyyContext, methods: CppyyMethods) -> object:
        assert self.__recursion >= 0
        assert self.__recursion <= 10
        self.__recursion += 1

        determinant = methods.determinant(context)
        if determinant.typename in self.__hints:
            self.__member__(self.__hints[determinant.typename], context, methods)
        elif determinant.typename in self.__handlers:
            methods.handler(context, self.__handlers[self.__handlers.index(determinant.typename)])
        else:
            self.__auto__(context, methods)

        self.__recursion -= 1
        return context.output.object

    def __auto__(self, context: CppyyContext, methods: CppyyMethods):
        determinant = methods.determinant(context)
        for member in vars(determinant.type):
            if (member[:2] == '__' and member[-2:] == '__') or member[:1] == '_':
                continue

            methods.auto(self.__get_context__(context.output.object, context.input.object, member, self))
            
    def __member__(self, hint: CppyyTypeHint, context: CppyyContext, methods: CppyyMethods):
        for member in hint.members_to_serialize:
            methods.member(self.__get_context__(context.output.object, context.input.object, member, self))
    
    @classmethod
    def __get_context__(cls, output: object, input:object, member: str, serializer: object) -> CppyyContext:
        return CppyyContext(
            output=CppyySerializeObject.from_object(output),
            input=CppyySerializeObject.from_object(input),
            member=member,
            serializer=serializer,
        )