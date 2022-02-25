import asyncio
import inspect
import unittest
from abc import ABCMeta
from typing import List, Tuple, Set, Generic, TypeVar

from botox import Injector, DeliveryError, PreparationError, SequenceInjection


class TestValueInjection(unittest.TestCase):

    def test_should_deliver_value(self):
        class MyService:
            pass

        singleton = MyService()

        injector = Injector()
        injector.prepare(MyService, singleton)

        self.assertIs(singleton, injector.deliver(MyService))


class TestLambdaInjection(unittest.TestCase):

    def test_should_deliver_lambda_return_value(self):
        class MyService:
            pass

        injector = Injector()
        injector.prepare(MyService, lambda: MyService())

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_none_value(self):
        class MyService:
            pass

        injector = Injector()
        injector.prepare(MyService, lambda: None)

        self.assertIsNone(injector.deliver(MyService))

    def test_should_raise_preparation_error_when_lambda_has_arguments(self):
        class MyService:
            pass

        injector = Injector()

        with self.assertRaises(PreparationError):
            injector.prepare(MyService, lambda argument: MyService())


class TestClassInjection(unittest.TestCase):

    def test_should_deliver_class_instance_when_specified(self):
        class MyService:
            pass

        injector = Injector()
        injector.prepare(MyService, MyService)

        a = injector.deliver(MyService)
        b = injector.deliver(MyService)

        self.assertIsInstance(a, MyService)
        self.assertIsNot(a, b)

    def test_should_deliver_class_instance_with_default_constructor(self):
        class MyService:
            pass

        injector = Injector()
        injector.prepare(MyService)

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_class_instance_with_custom_constructor(self):
        class MyService:
            def __init__(self):
                pass

        injector = Injector()
        injector.prepare(MyService)

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_class_instance_with_one_dependency(self):
        class MyService:
            pass

        class MyFacade:
            def __init__(self, service: MyService) -> None:
                self.service = service

        injector = Injector()
        injector.prepare(MyService)
        injector.prepare(MyFacade)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.service, MyService)

    def test_should_deliver_class_instance_with_many_dependencies(self):
        class MyService:
            pass

        class OtherService:
            pass

        class MyFacade:
            def __init__(self, my_service: MyService, other_service: OtherService) -> None:
                self.my_service = my_service
                self.other_service = other_service

        injector = Injector()
        injector.prepare(MyService)
        injector.prepare(OtherService)
        injector.prepare(MyFacade)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.my_service, MyService)
        self.assertIsInstance(facade.other_service, OtherService)

    def test_should_deliver_class_instance_with_kwargs(self):
        class MyService:
            def __init__(self, option=None):
                pass

        injector = Injector()
        injector.prepare(MyService)

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_class_instance_with_one_kwarg_dependency(self):
        class MyService:
            pass

        class MyFacade:
            def __init__(self, service: MyService = None) -> None:
                self.service = service

        injector = Injector()
        injector.prepare(MyService)
        injector.prepare(MyFacade)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.service, MyService)

    def test_should_deliver_class_instance_with_deep_dependencies(self):
        class MyRepository:
            pass

        class MyService:
            def __init__(self, repository: MyRepository):
                self.repository = repository

        class MyAdapter:
            def __init__(self, service: MyService):
                self.service = service

        class MyFacade:
            def __init__(self, service: MyService, adapter: MyAdapter):
                self.service = service
                self.adapter = adapter

        injector = Injector()
        injector.prepare(MyFacade)
        injector.prepare(MyService)
        injector.prepare(MyRepository)
        injector.prepare(MyAdapter)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.service, MyService)
        self.assertIsInstance(facade.service.repository, MyRepository)
        self.assertIsInstance(facade.adapter, MyAdapter)
        self.assertIsNot(facade.service, facade.adapter.service)
        self.assertIsNot(facade.service.repository, facade.adapter.service.repository)

    def test_should_deliver_concrete_implementation(self):
        class AbstractService:
            pass

        class ConcreteService(AbstractService):
            pass

        injector = Injector()
        injector.prepare(AbstractService, ConcreteService)

        self.assertIsInstance(injector.deliver(AbstractService), ConcreteService)

    def test_should_raise_delivery_error_when_dependency_not_prepared(self):
        class MyService:
            pass

        class MyFacade:
            def __init__(self, service: MyService):
                pass

        injector = Injector()
        injector.prepare(MyFacade)

        with self.assertRaises(DeliveryError):
            injector.deliver(MyFacade)


class TestFunctionInjection(unittest.TestCase):

    def test_should_deliver_function_return_value_when_no_arguments(self):
        class MyService:
            pass

        def create_service():
            return MyService()

        injector = Injector()
        injector.prepare(MyService, create_service)

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_bound_method_return_value_when_no_arguments(self):
        class MyService:
            pass

        class App:
            def create_service(self):
                return MyService()

        injector = Injector()
        injector.prepare(MyService, App().create_service)

        self.assertIsInstance(injector.deliver(MyService), MyService)

    def test_should_deliver_none_value(self):
        class MyService:
            pass

        def create_service():
            return None

        injector = Injector()
        injector.prepare(MyService, create_service)

        self.assertIsNone(injector.deliver(MyService))

    def test_should_raise_preparation_error_when_function_has_arguments(self):
        class MyService:
            pass

        injector = Injector()

        def create_service(argument):
            return MyService()

        with self.assertRaises(PreparationError):
            injector.prepare(MyService, create_service)

    def test_should_return_function_return_value_with_dependency(self):
        class MyService:
            pass

        class MyFacade:
            def __init__(self, service):
                self.service = service

        def create_facade(service: MyService):
            return MyFacade(service)

        injector = Injector()
        injector.prepare(MyService)
        injector.prepare(MyFacade, create_facade)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.service, MyService)

    def test_should_return_bound_method_return_value_with_dependency(self):
        class MyService:
            pass

        class MyFacade:
            def __init__(self, service):
                self.service = service

        class App:
            def create_facade(self, service: MyService):
                return MyFacade(service)

        injector = Injector()
        injector.prepare(MyService)
        injector.prepare(MyFacade, App().create_facade)

        facade = injector.deliver(MyFacade)
        self.assertIsInstance(facade, MyFacade)
        self.assertIsInstance(facade.service, MyService)


class TestInjectorCreation(unittest.TestCase):

    def test_should_not_affect_parent_injector(self):
        parent = Injector()
        parent.prepare(str, 'alice')

        child = parent.create()
        child.prepare(str, 'boris')

        self.assertEqual('alice', parent.deliver(str))
        self.assertEqual('boris', child.deliver(str))


class TestInject(unittest.TestCase):

    def test_should_apply_dependency_araguments_partially(self):
        class MyService:
            pass

        def target(a, b, service: MyService):
            return service

        injector = Injector()
        injector.prepare(MyService)

        target = injector.inject(target, skip=2)
        self.assertIsInstance(target(1, 2), MyService)

    def test_should_return_instrumented_coroutine_when_injecting_to_coroutine(self):
        class Foo:
            pass

        async def async_handler(foo: Foo):
            return foo

        injector = Injector()
        injector.prepare(Foo)

        target = injector.inject(async_handler)
        self.assertTrue(inspect.iscoroutinefunction(target))

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(target())
        self.assertIsInstance(result, Foo)


class TestSequenceInjection(unittest.TestCase):

    def test_should_deliver_list_with_dependencies(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class GooglePayService(PaymentService):
            pass

        class ApplePayService(PaymentService):
            pass

        injector = Injector()
        injector.prepare(GooglePayService)
        injector.prepare(ApplePayService)
        injector.prepare(List[PaymentService], [GooglePayService, ApplePayService])

        services = injector.deliver(List[PaymentService])
        self.assertIsInstance(services, list)
        self.assertEqual(len(services), 2)
        self.assertIsInstance(services[0], GooglePayService)
        self.assertIsInstance(services[1], ApplePayService)

    def test_should_not_make_side_effect_when_list_with_dependencies_changed(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class GooglePayService(PaymentService):
            pass

        class ApplePayService(PaymentService):
            pass

        injector = Injector()
        injector.prepare(GooglePayService)
        injector.prepare(ApplePayService)
        injector.prepare(List[PaymentService], [GooglePayService, ApplePayService])

        services = injector.deliver(List[PaymentService])
        services.pop(0)

        services = injector.deliver(List[PaymentService])
        self.assertIsInstance(services, list)
        self.assertEqual(len(services), 2)
        self.assertIsInstance(services[0], GooglePayService)
        self.assertIsInstance(services[1], ApplePayService)

    def test_should_deliver_custom_sequence_data_type_with_dependencies(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class GooglePayService(PaymentService):
            pass

        class ApplePayService(PaymentService):
            pass

        T = TypeVar('T')

        class MyCollection(Generic[T], list):
            pass

        injector = Injector()
        injector.prepare(GooglePayService)
        injector.prepare(ApplePayService)

        injection = SequenceInjection(MyCollection, [GooglePayService, ApplePayService])
        injector.prepare(MyCollection[PaymentService], injection)

        services = injector.deliver(MyCollection[PaymentService])
        self.assertIsInstance(services, MyCollection)
        self.assertEqual(len(services), 2)
        self.assertIsInstance(services[0], GooglePayService)
        self.assertIsInstance(services[1], ApplePayService)

    def test_should_deliver_tuple_with_dependencies(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class GooglePayService(PaymentService):
            pass

        class ApplePayService(PaymentService):
            pass

        injector = Injector()
        injector.prepare(GooglePayService)
        injector.prepare(ApplePayService)
        injector.prepare(Tuple[PaymentService], [GooglePayService, ApplePayService])

        services = injector.deliver(Tuple[PaymentService])
        self.assertIsInstance(services, tuple)
        self.assertEqual(len(services), 2)
        self.assertIsInstance(services[0], GooglePayService)
        self.assertIsInstance(services[1], ApplePayService)

    def test_should_deliver_set_with_dependency(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class ApplePayService(PaymentService):
            pass

        injector = Injector()
        injector.prepare(ApplePayService)
        injector.prepare(Set[PaymentService], [ApplePayService])

        services = injector.deliver(Set[PaymentService])
        self.assertIsInstance(services, set)
        self.assertIsInstance(services.pop(), ApplePayService)

    def test_should_deliver_nested_sequence_injection_when_tuple_in_list(self):
        class PaymentService(metaclass=ABCMeta):
            pass

        class GooglePayService(PaymentService):
            pass

        class ApplePayService(PaymentService):
            pass

        injector = Injector()
        injector.prepare(GooglePayService)
        injector.prepare(ApplePayService)
        injector.prepare(Tuple[PaymentService], [GooglePayService, ApplePayService])
        injector.prepare(List[Tuple[PaymentService]], [Tuple[PaymentService]])

        container = injector.deliver(List[Tuple[PaymentService]])
        self.assertIsInstance(container, list)
        self.assertEqual(len(container), 1)
        services = container[0]
        self.assertIsInstance(services, tuple)
        self.assertIsInstance(services[0], GooglePayService)
        self.assertIsInstance(services[1], ApplePayService)
