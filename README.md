# Botox

Botox Injector is a dependency injection implementation based on Python type annotations.
It helps deliver the configured functional objects, decreasing coupling between a class and its dependencies.

### Delivery 

Global variables? Proxy objects? Application context?

There should be one (and preferably only one) obvious way to do it.

Botox helps you isolate a class from the impact of different design changes and defects. 
Meaning that, instead of thinking about interdependence between application modules
you will now find yourself spending your time having to focus a class on the task it is designed for.

### Configuration

Monkey-patching? Decorators?

Explicit is better than implicit.

Botox allows a class the flexibility of being configurable.
The class rely on dependencies interface that he expect.
Explicit configurations can be written separately for different
situations that require different implementations of dependencies.
  
### Usage

Now is better than never.

Botox doesn’t require any change in code behavior it can be applied to legacy code as a refactoring.

## Installation

Install and update using [pip](https://pip.pypa.io/en/stable/quickstart/):

```bash
pip install -U botox-di
```

## Examples

### Class Injection

Can be used to reduce boilerplate code in the application classes since 
all work to initialize or set up dependencies is handled separately.

```python
from botox import Injector

class PaymentService:
    ...
    
class BillingService:
    ...
    
class SalesService:

    def __init__(self, payment_service: PaymentService, billing_service: BillingService):
        self.payment_service = payment_service
        self.billing_service = billing_service
   
injector = Injector()
injector.prepare(PaymentService)
injector.prepare(BillingService)
injector.prepare(SalesService)

sales = injector.deliver(SalesService)

assert isinstance(sales.payment_service, PaymentService)
assert isinstance(sales.billing_service, BillingService)
```

The result is class that is easier to unit test in 
isolation using stubs or mock objects that simulate other objects.

```python
injector.prepare(PaymentService, PaymentServiceStub)
```

### Value Injection

Can be used when exactly one object is needed to coordinate actions across the system.

```python
from botox import Injector

class AppSettings:
    ...
    
settings = AppSettings()

injector = Injector()
injector.prepare(AppSettings, settings)

assert injector.deliver(AppSettings) is settings
```

### Lambda Injection

Can be used to wrap Proxy objects in legacy code as refactoring.

```python
from botox import Injector
from flask import g
from sqlalchemy.orm import Session

injector = Injector()
injector.prepare(Session, lambda: g.session)
```

### Function Injection

Can be used to make factory functions with dependencies.

```python
from botox import Injector

def create_api_client(settings: Settings):
    return ApiClient(settings.base_url, settings.key)
    
injector = Injector()
injector.prepare(Settings)
injector.prepare(ApiClient, create_api_client)
```

### Sequence Injection

Can be used to provide collection of dependencies.

```python
class PaymentService(metaclass=ABCMeta):
    name: str
    
class GooglePayService(PaymentService):
    ...
    
class ApplePayService(PaymentService):
    ...

class FlowService:

    def __init__(self, payment_services: List[PaymentService]):
        self.payment_services = payment_services
        
    def get_available_payment_methods(self):
        for payment_service in self.payment_services:
            yield payment_service.name
    
injector = Injector()
injector.prepare(GooglePayService)
injector.prepare(ApplePayService)
injector.prepare(List[PaymentService], [GooglePayService, ApplePayService])
injector.prepare(FlowService)

```

### AIOHTTP

You can use a middleware to deliver dependencies into a request handler. Asynchronous functions also supported.

```python
from aiohttp import web
from botox import Injector

class HelloService:
    def get_hello_message(self, name):
        return f'Hello, {name}!'

async def handle(request, service: HelloService):
    name = request.match_info.get('name', 'Anonymous')
    text = service.get_hello_message(name)
    return web.Response(text=text)

@web.middleware
async def dependency_injection(request, handler):
    handler = request.app.injector.inject(handler, skip=1)
    return await handler(request)

app = web.Application(middlewares=[dependency_injection])
app.injector = Injector()
app.injector.prepare(HelloService)
app.add_routes([
    web.get('/', handle),
    web.get('/{name}', handle)
])

web.run_app(app)
```

### FastAPI

You can use Botox together with the built-in dependency system of FastAPI.

```python
from botox import Injector
from fastapi import Depends, FastAPI

class HelloService:
    def get_hello_message(self, name):
        return f'Hello, {name}!'

app = FastAPI(openapi_url=None)
app.injector = Injector()
app.injector.prepare(HelloService)

def inject(token: Type[T]) -> T:
    async def _get_dependency(request: Request):
        return request.app.injector.deliver(token)

    return Depends(_get_dependency, use_cache=False)

@app.get("/{name}")
async def handle(name: str, service=inject(HelloService)):
    return service.get_hello_message(name)

```

### Celery

You can define a different application base task class to deliver dependencies into a task call.

```python
from celery import Celery, Task
from botox import Injector

class Calculator:
    def add(self, x, y):
        return x + y

class AppTask(Task):
    def __call__(self, *args, **kwargs):
        run = self.app.injector.inject(self.run, skip=len(args))
        return run(*args, **kwargs)

app = Celery('tasks', broker='pyamqp://guest@localhost//', task_cls=AppTask)
app.injector = Injector()
app.injector.prepare(Calculator)

@app.task
def add(x, y, calculator: Calculator):
    return calculator.add(x, y)
```