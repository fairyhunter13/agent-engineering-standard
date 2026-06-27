---
name: test-data-builders
description: Use the Builder pattern for test data to eliminate duplicated setup code, reduce test fragility on model changes, and improve readability.
discipline: qa
tags: [testing, test-data, builders, fixtures, readability]
---

# Test Data Builders

## When to use
Apply this skill when test setup code is duplicated across many test files, when changing a domain model requires updating dozens of test fixtures, when tests have more setup lines than assertion lines, or when it is hard to tell what a test is actually asserting because setup noise dominates.

## Signal
- `User(name="test", email="test@test.com", role="admin", age=30, ...)` repeated verbatim across 20+ test files.
- A new required field on `Order` breaks 40 tests because they all construct `Order` directly.
- Test fixture JSON files are maintained by hand and frequently out of sync with the model.
- Test setup is 50+ lines; the actual assertion is 2 lines.
- Copy-pasting an existing test to write a new one because setup is too expensive to recreate from scratch.
- No distinction between "fields this test cares about" and "fields required to make the object valid."

## Why
Duplicated, verbose test data setup makes tests fragile (model changes break everything), hard to read (intent obscured by noise), and slow to write (each new test requires full setup). The Test Data Builder pattern (Nat Pryce, 2007) centralizes default values in one place, exposes only the fields each test cares about, and decouples tests from the full model structure. When a new required field is added to `User`, only the `UserBuilder` needs to be updated — not every test.

## Remediate

1. **Create a Builder class with sensible defaults.** The builder constructs a valid, minimal object by default. Tests override only the fields relevant to their assertion:
   ```ts
   // TypeScript — UserBuilder
   class UserBuilder {
     private props: Partial<User> = {
       id: 'user-default-id',
       name: 'Test User',
       email: 'test@example.com',
       role: 'member',
       isActive: true,
       createdAt: new Date('2024-01-01'),
     };

     withRole(role: UserRole): this {
       this.props.role = role;
       return this;
     }

     withEmail(email: string): this {
       this.props.email = email;
       return this;
     }

     inactive(): this {
       this.props.isActive = false;
       return this;
     }

     build(): User {
       return new User(this.props as UserProps);
     }
   }

   // Usage — test only cares about role
   const admin = new UserBuilder().withRole('admin').build();
   const inactiveUser = new UserBuilder().inactive().build();
   ```

2. **Use a factory library instead of writing builders manually.** Libraries provide generators, sequences, and relationship handling out of the box:
   - TypeScript/JavaScript: `fishery`
     ```ts
     const userFactory = Factory.define<User>(() => ({
       id: faker.string.uuid(),
       name: faker.person.fullName(),
       email: faker.internet.email(),
       role: 'member',
     }));
     const admin = userFactory.build({ role: 'admin' });
     const [user1, user2] = userFactory.buildList(2);
     ```
   - Python: `factory_boy`
     ```python
     class UserFactory(factory.Factory):
         class Meta:
             model = User
         name = factory.Faker('name')
         email = factory.Faker('email')
         role = 'member'
         is_active = True

     admin = UserFactory(role='admin')
     ```
   - Java: `easy-random` or `instancio`

3. **Keep builders in a dedicated directory.** Organize factories/builders alongside tests, not buried in test files:
   ```
   tests/
     factories/
       user-factory.ts
       order-factory.ts
       product-factory.ts
     unit/
       user-service.test.ts
     integration/
       checkout.test.ts
   ```

4. **Chain builders for relationships.** When building related objects, chain builders:
   ```ts
   const orderWithPremiumUser = new OrderBuilder()
     .withUser(new UserBuilder().withRole('premium').build())
     .withItems([new OrderItemBuilder().withQuantity(3).build()])
     .build();
   ```
   Factory libraries handle this more elegantly with traits and associations:
   ```ts
   const orderFactory = Factory.define<Order>(({ associations }) => ({
     user: associations.user ?? userFactory.build(),
     items: [],
   }));
   const order = orderFactory.build({ user: userFactory.build({ role: 'premium' }) });
   ```

5. **Use sequences for unique fields.** When a field must be unique per test (email, username, order number), use a sequence to avoid collisions:
   ```ts
   // fishery sequence
   const userFactory = Factory.define<User>(({ sequence }) => ({
     email: `user-${sequence}@example.com`,
     username: `user${sequence}`,
   }));
   ```
   ```python
   # factory_boy sequence
   class UserFactory(factory.Factory):
       email = factory.Sequence(lambda n: f'user{n}@example.com')
   ```

6. **Write "builder fluency" documentation inline.** Add a comment block to each builder listing common usage patterns. This is the documentation developers actually read:
   ```ts
   /**
    * UserBuilder — builds valid User objects for tests.
    * Common patterns:
    *   new UserBuilder().build()              → standard member
    *   new UserBuilder().withRole('admin')    → admin user
    *   new UserBuilder().inactive()           → soft-deleted user
    *   new UserBuilder().withEmail('x@y.com') → specific email
    */
   ```

7. **Persist to DB within the factory for integration tests.** For integration tests that require DB-persisted objects, add a `create()` method that saves via the ORM:
   ```ts
   async create(): Promise<User> {
     return await prisma.user.create({ data: this.props as UserCreateInput });
   }
   // Usage
   const user = await new UserBuilder().withRole('admin').create();
   ```

## References
- Nat Pryce — "Test Data Builders" (nat.tc/test-data-builders, 2007)
- fishery (thoughtbot/fishery) — TypeScript factory library
- factory_boy (FactoryBoy/factory_boy) — Python factory library
- instancio (instancio/instancio) — Java object builder for tests
