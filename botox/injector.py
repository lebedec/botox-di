from abc import ABCMeta
from functools import lru_cache, wraps
from inspect import signature, iscoroutinefunction
from types import LambdaType, FunctionType, MethodType
from typing import TypeVar, Type, List, Any, Callable, Dict, Optional, Tuple, Set

__all__ = [
    'Injector',
    'DependencyInjectionError',
    'PreparationError',
    'DeliveryError',
    'ValueInjection',
    'ClassInjection',
    'LambdaInjection',
    'FunctionInjection',
    'SequenceInjection'
]

T = TypeVar('T')

Token = Type[T]

DependencyPath = List[Tuple[int, Callable]]


class DependencyInjectionError(Exception):
    pass


class PreparationError(DependencyInjectionError):
    pass


class DeliveryError(DependencyInjectionError):
    pass


class Injection(metaclass=ABCMeta):

    @property
    def ingredients(self) -> List[Token]:
        """
        A list of `DependencyToken`s which need to be resolved by the `Injector` before deliver.
        """
        raise NotImplementedError()

    def deliver(self, dependencies: List) -> Any:
        raise NotImplementedError()


class ValueInjection(Injection):
    """
    Configures the `Injector` to return a value for a dependency token.
    """

    def __init__(self, value: Any):
        self._value = value

    @property
    def ingredients(self) -> List[Token]:
        return []

    def deliver(self, dependencies: List) -> Any:
        return self._value


class ClassInjection(Injection):
    """
    Configures the `Injector` to return an instance of class for a dependency token.
    """

    def __init__(self, _class: Type):
        self._class = _class

    @property
    def ingredients(self) -> List[Token]:
        init_function = self._class.__init__
        if init_function is object.__init__:
            return []
        else:
            references = init_function.__annotations__.items()
            tokens = [token for name, token in references if name != 'return']
            return tokens

    def deliver(self, dependencies: List) -> Any:
        return self._class(*dependencies)


class LambdaInjection(Injection):
    """
    Configures the `Injector` to return a dependency by invoking lambda.
    """

    def __init__(self, _lambda: LambdaType):
        self._lambda = _lambda

    @property
    def ingredients(self) -> List[Token]:
        return []

    def deliver(self, dependencies: List) -> Any:
        return self._lambda()


class FunctionInjection(Injection):
    """
    Configures the `Injector` to return a dependency by invoking function or bound method.
    """

    def __init__(self, function: Callable):
        self._function = function

    @property
    def ingredients(self) -> List[Token]:
        references = self._function.__annotations__.items()
        tokens = [token for name, token in references if name != 'return']
        return tokens

    def deliver(self, dependencies: List) -> Any:
        return self._function(*dependencies)


class SequenceInjection(Injection):
    """
    Configures the `Injector` to return collection of dependencies.
    """

    def __init__(self, sequence_data_type, tokens: List[Token]):
        self._tokens = tokens
        self._sequence_data_type = sequence_data_type

    @property
    def ingredients(self) -> List[Token]:
        return self._tokens

    def deliver(self, dependencies: List) -> Any:
        return self._sequence_data_type(dependencies)


class Injector:

    def __init__(self, cache=None):
        self._injections: Dict[Token, Injection] = {}
        if cache is None:
            cache = lru_cache()
        self._find_path_method = cache(self._find_path)

    def create(self) -> 'Injector':
        """
        Creates a new Injector which contains all prepared injections.
        Can be used to organize dependency scopes.
        """
        injector = Injector()
        injector._injections = self._injections.copy()
        return injector

    def inject(self, target: Callable, skip=0, strict=True):
        def _resolve_args(*args):
            parameters = list(signature(target).parameters.values())[skip:]
            dependencies = tuple(self.deliver(p.annotation, strict) for p in parameters)
            args = args + dependencies
            return args

        @wraps(target)
        def wrapper(*args, **kwargs):
            return target(*_resolve_args(*args), **kwargs)

        @wraps(target)
        async def async_wrapper(*args, **kwargs):
            return await target(*_resolve_args(*args), **kwargs)

        return async_wrapper if iscoroutinefunction(target) else wrapper

    def prepare(self, token: Token, value: Any = None) -> None:
        if isinstance(value, Injection):
            injection = value

        elif hasattr(token, '__origin__') and issubclass(token.__origin__, List):
            injection = SequenceInjection(list, value)

        elif hasattr(token, '__origin__') and issubclass(token.__origin__, Tuple):
            injection = SequenceInjection(tuple, value)

        elif hasattr(token, '__origin__') and issubclass(token.__origin__, Set):
            injection = SequenceInjection(set, value)

        elif isinstance(value, type):
            injection = ClassInjection(value)

        elif isinstance(value, FunctionType) and '<lambda>' in value.__name__:
            if value.__code__.co_argcount:
                raise PreparationError(
                    f'Unable to prepare token={token} injection, '
                    f'lambda has arguments'
                )
            injection = LambdaInjection(value)

        elif isinstance(value, MethodType):
            injection = FunctionInjection(value)

        elif isinstance(value, FunctionType):
            if value.__code__.co_argcount and not len(value.__annotations__):
                raise PreparationError(
                    f'Unable to prepare token={token} injection, '
                    f'function {value} has arguments but no annotations'
                )
            injection = FunctionInjection(value)

        elif value is None:
            injection = ClassInjection(token)

        else:
            injection = ValueInjection(value)

        self.prepare_injection(token, injection)

    def prepare_injection(self, token: Token, injection: Injection) -> None:
        if not isinstance(injection, Injection):
            raise PreparationError(
                f'Unable to prepare token={token} injection, '
                f'argument must be instance of Injection class'
            )
        self._injections[token] = injection

    def deliver(self, token: Token, strict=True) -> Optional[T]:
        """
        :param token: Dependency class used as token.
        :param strict: Strict mode eliminates dependency configuration silent errors by changing them to exceptions.
        :return: An instance of dependency based on the specified 'token'.
        """
        path = self._find_path_method(token, strict)
        instances = []
        index = 0
        for argn, deliver in reversed(path):
            instances.append(deliver(reversed(instances[index:index + argn])))
            index += argn
        return instances[-1]

    def _find_path(self, token: Token, strict=True) -> DependencyPath:
        """
        Converts dependency definitions into a flat array of resolved injection deliver methods.
        This path can be cached to increase delivery speed.
        """
        path = []
        queue = [token]
        while queue:
            token = queue.pop(0)
            injection = self._injections.get(token, None)
            if injection is None:
                if strict:
                    raise DeliveryError(
                        f'Dependency injection token={token} not configured,'
                        f'try Injector.prepare before deliver'
                    )
                path.append((0, None))

            ingredients = injection.ingredients
            path.append((len(ingredients), injection.deliver))
            for ingredient in ingredients:
                queue.append(ingredient)

        return path
