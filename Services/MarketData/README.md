# Market Data service

Fetches **daily** stock bars from Yahoo Finance, stores them durably in MSSQL, and announces new data by delivering a signed `MarketDataRefreshed` webhook to subscribers (via a transactional outbox).

### Folder structure
```
|_app
  _api (holds all the api end points and incoming request processing)
  _domain (holds the models)
|_db

|_tests

Dockerfile

config.py

config.template.py

README.md

pyproject.toml
```

#### How to tag and push docker images locally (with k3s)

```
step 1
sudo docker run -d \
  --name local-registry \
  --restart=always \
  -p 5001:5000 \
  registry:2

step 2
sudo vim /etc/rancher/k3s/registries.yaml
step 3 > paste the below block
mirrors:
  "localhost:5001":
    endpoint:
      - "http://localhost:5001"

step 4
sudo systemctl restart k3s

repeating steps for development:
sudo docker build -t localhost:5001/market-data:latest .
sudo docker push localhost:5001/market-data:latest
kubectl rollout restart deployment market-data

```

### Concepts to Learn
---
#### @dataclass(frozen=True)
makes an instance of a data class immutable. Once an object is created, you cannot change or delete its attributes.

When to Use It

• Value objects / DTOs (Data Transfer Objects): When you want to pass data around safely without accidental side effects or state mutations.

• Constants or configuration models: When the data should remain fixed for the lifetime of the object.

• Dictionary keys / Set items: When you need a custom composite key that requires hashing.

---
#### from \_\_future\_\_ import annotations
This tells Python: “when the code is parsed, don’t evaluate type annotations immediately; treat them as postponed strings.”

Without it, this can fail:

```
class A:
    b: B

class B:
    pass
```

because B is not defined yet when A is created.

---
#### from typing import Protocol
A Protocol lets you define an interface based on what an object can do (its methods and attributes).

primarily used with static type checkers that recognize structural subtyping (static duck-typing).

In this project, and generally in Python, we use Protocols to create contracts.

---
#### Contracts

A code contract specifies what a component expects from the outside world and what it guarantees in return.

If you come from languages like Java or C#, a Protocol serves the exact same architectural purpose as an Interface. The only difference is that Python's version is "implicit"—if an object looks like the interface and acts like the interface, Python considers the contract signed and honored.


---
#### pyproject.toml
is a human-readable configuration file format used heavily across the Python ecosystem to store metadata, project settings, and tool configurations.

---
#### Ports & Adapters Pattern (AKA Hexagonal Architecture)
a software design pattern to isolate core business logic from external technologies, frameworks, and user interfaces.

**Application Core** -> Business Logic: Sits at the center (the "hexagon"), housing pure domain models, rules, and use cases.

**Ports** ->  Act as contracts defined by the application core to handle incoming or outgoing communication.

Driving Ports -> Expose application use cases to the outside world

Driven Ports -> Define what the application core needs from external resources

**Adapters** ->  Bridge the gap between the application's ports and the external world.

Driving Adapters ->  Translate external triggers (like an HTTP request from a REST controller or a CLI command) into calls to the application's primary ports.

Driven Adapters -> Implement the application's secondary ports to talk to external systems (such as a PostgreSQL database driver, a Redis cache, or a third-party payment API)

**Considerations** -> While it can cause potentially more maintenance overhead and latency issues due to extra layers . It can work especially well with **Domain-Driven Design** , can be used to achieve loose coupling among application components, and since this pattern uses abstractions for inputs and outputs. Therefore, writing unit tests and testing in isolation become easier because of the inherent loose coupling.

Further: https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/hexagonal-architecture.html

---

#### Repository Design Pattern
acts as an abstraction layer between an application's business logic and its underlying data persistence store (e.g., SQL Server)

It mimics an in-memory collection of domain objects, hiding the complex details of how data is fetched, saved, updated, or deleted from a database or external API. Therefore, business logic does not need to know where the data is coming from and is not technology-bound which improves testability and the domain model remains independant of infrastructure details.

**Components:** 

1- Domain Model/Entity (core business object)., 

2- Repository Interface (A contract defining what data operations are allowed)

3- Concrete Implementations (The actual class that talks to the database)

---

#### Unit of Work Design Pattern
This behavioural design pattern abstract the concept of **Database Transactions**, ensuring that either all grouped database operations succeed together or all fail together.

The Unit of Work (The Orchestrator) tracks changes (Created, Modified, Deleted) during a transaction. It holds a reference to the database context and exposes a final Commit() or SaveChanges() method to execute all operations atomically.

---

#### Anti-Corruption Layer Design Pattern (ACL)

It places a translation and isolation boundary between two incompatible subsystems. It is aiming to stop external naming conventions, database schemas, and awkward business semantics (like numeric status codes or foreign data structures) from leaking into and polluting your core application design & allow the modern system and the legacy or external system to evolve independently without breaking each other.

Its common use cases are 1- legacy application migrations, 2- third-party integrations, 3- bounded context integration.

It can be either a set of classes and components within an application or be deployed as a stand-alone microservice.

Its main duties are 1- data translation (converting incoming and outgoing data structures), 2- request translation, and 3- data validation and sanitization

---

#### Transactional Outbox Design Pattern

It solves the "dual-write problem" in distributed and microservice systems when you need to update a database and publish an event to a message broker (like Kafka or RabbitMQ) at the same time.


How It Works

1. Atomic Local Transaction: Instead of writing to the database and calling the message broker separately, the service writes the business data change and an outbox message (or event record) into the same local database transaction. Both commit or roll back together.
2. Outbox Storage:
	• Relational databases: A dedicated outbox table stores the payloads to be sent.
	• NoSQL databases: The outbox is stored as a field or document property inside the record.
3. Asynchronous Relay: A separate background process or relay reads the un-dispatched outbox records and publishes them to the message broker.
4. Mark or Delete: After successful publishing, the relay marks the record as processed or deletes it.

---

#### Idempotent Upsert Design Pattern

Inserts a new record if it does not exist or updates the existing record if it does, ensuring that running the exact same operation multiple times leaves the target database or pipeline in the same final state.

----

#### Retry with Exponential Backoff Design Pattern

An error-handling strategy where a system repeatedly attempts a failed operation (like a network call or database query) with an increasing time delay between each try. Typically, the wait time doubles or multiplies with each failure

---