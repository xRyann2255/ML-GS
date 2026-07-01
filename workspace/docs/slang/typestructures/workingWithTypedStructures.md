# Working with Typed Structures in Slang

## Overview

Typed Structures are Slang's mechanism for defining **object-like types** with typed data members and member functions. Think of them as Slang's equivalent of classes. They support inheritance, interfaces, packages, static members, operator overriding, and reference counting.

> For plain key-value containers (Structure, StructureCase, GStructure), see `.github/structures/`.

## Defining a Typed Structure

### TypeDefine (Non-Streamable)

The most common form. Non-streamable types cannot be serialized to binary or saved to the database.

```slang
TypeDefine( "My Namespace::My Type" )
{
    // Member functions
    Greet = Func( Self )
    Returns( String() )
    {
        Return( Sprintf( "Hello, %s!", Self.Name ) );
    };

    // Members block (MUST be last)
    Members()
    {
        String( Name ) := "World",
        Double( Age )  := 0,
    };
};
```

**Critical rules:**
- `Scope::Name` -- Scope and Name **must differ** (e.g., `"ABC::Test"` not `"ABC::ABC"`)
- The `Members()` block must be the **last block** inside `TypeDefine`
- Every member function's first argument must be `Self`

### TypeDefineStreamable

For types that need to be serialized. Requires a globally unique integer TypeID:

```slang
TypeDefineStreamable( 12345, "My Namespace::Streamable Type" )
{
    Members()
    {
        String( Data ) := "",
    };
};
```

> **Warning:** While streamable types *can* be persisted to the database, it is **not recommended** -- the streaming logic is fragile. Use UFOs instead.

### TypeDefineInterface

Defines a contract that typed structures can implement. Similar to Java interfaces:

```slang
TypeDefineInterface( "My Namespace::Printable" )
{
    To String = Func( Self ) Returns( String() ) { };
};
```

### TypeDefinePackage

A reusable bundle of functions that can be imported into multiple types. Like a mixin:

```slang
TypeDefinePackage( "My Namespace::Logging" )
{
    Log = Func( Self, String( Message ) )
    Returns()
    {
        Printf( "[LOG] %s: %s\n", Self.Name, Message );
    };

    ContractMembers()
    {
        String( Name ),
    };
};
```

## Instantiation

Three equivalent ways to create an instance:

```slang
X = My Namespace::My Type();                        // preferred
X = Typed Structure( "My Namespace::My Type" );     // by string name
X = Apply( "My Namespace::My Type" );               // dynamic
```

Pass member values at construction time:

```slang
Person = My Namespace::My Type( Name := "Alice", Age := 30 );
```

## Linking

Non-streamable typed structures must be **explicitly linked** before use:

```slang
Link( "_TYPE My Type Definition" );
Instance = My Namespace::My Type();
```

Streamable typed structures do **not** need linking.

### Dynamic Linking with SmartLink

When the type name is only known at runtime:

```slang
SmartLink( Library Name );
Instance = Apply( Type Name );
```

## Accessing Members

```slang
Person = My Namespace::My Type( Name := "Alice" );

// Read
Print( Person.Name, "\n" );              // "Alice"

// Write
Person.Age = 25;
```

## Calling Member Functions

Use dot notation. **Do NOT use `@`** for member function calls:

```slang
// CORRECT
Greeting = Person.Greet();

// WRONG -- do not do this
Greeting = @Person.Greet();
```

## Msg New (Constructor)

`Msg New` is called during construction. It accepts **only `Self`** -- no other arguments:

```slang
TypeDefine( "ABC::Widget" )
{
    Msg New = Func( Self )
    Returns()
    {
        Self.Items = [];
        Self.Created At = Time();
    };

    Members()
    {
        Array( Items ),
        Any( Created At ) := Null,
    };
};
```

> **Critical:** `Msg New` does NOT accept extra arguments. Use named member defaults or set values after construction.

## Msg Overrides (Operator Overloading)

Typed Structures support overriding built-in message functions to customize construction, destruction, and native operators. The full list of supported Msg functions is documented in `_LIB Typed Structure Function`.

### Overridable Messages

You can override these special functions inside a `TypeDefine`:

| Msg Function | Purpose |
|-------------|---------|
| `Msg New` | Constructor (called on instantiation) |
| `Msg Destroy` | Destructor (called when instance is destroyed) |
| `Msg Copy` | Called when instance is copied |
| `Msg Add` | Override `+` operator |
| `Msg Subtract` | Override `-` operator |
| `Msg Multiply` | Override `*` operator |
| `Msg Divide` | Override `/` operator |
| `Msg Negate` | Override unary `-` operator |
| `Msg Compare` | Override comparison operators (`==`, `<`, etc.) |
| `Msg String` | Override `String()` cast |
| `Msg Print` | Override `Print()` output |

### Example: Overriding Operators

See `Example: Typed Structure Ops` and `Example: Typed Structure Ops1` for full working examples.

```slang
TypeDefine( "ABC::Vector2D" )
{
    Msg Add = Func( Self, ABC::Vector2D( Other ) )
    Returns( ABC::Vector2D() )
    {
        Return( ABC::Vector2D( X := Self.X + Other.X, Y := Self.Y + Other.Y ) );
    };

    Msg String = Func( Self )
    Returns( String() )
    {
        Return( Sprintf( "(%d, %d)", Self.X, Self.Y ) );
    };

    Members()
    {
        Double( X ) := 0,
        Double( Y ) := 0,
    };
};

A = ABC::Vector2D( X := 1, Y := 2 );
B = ABC::Vector2D( X := 3, Y := 4 );
C = A + B;
Print( C, "\n" );                  // "(4, 6)"
```

### Gotcha: `+=` vs Explicit Add-and-Assign

Be careful with the right-hand side referencing a component that doesn't exist yet:

```slang
// WRONG -- redboxes because x.GBP doesn't exist when the RHS is evaluated
X = {||};
X.GBP = X.GBP + 100;

// CORRECT -- += handles creation and assignment atomically
X = {||};
X.GBP += 100;                     // Works, X.GBP is now 100
```

This applies to both Structures and Typed Structures.

## Inheritance

Specify a base type in the `Members()` declaration:

```slang
TypeDefine( "ABC::Base" )
{
    Greet = Func( Self )
    Returns( String() )
    {
        Return( "Hello" );
    };

    Members()
    {
        String( Name ) := "",
    };
};

TypeDefine( "ABC::Child" )
{
    // Override the base function
    Greet = Func( Self )
    Returns( String() )
    {
        Return( "Hola" );
    };

    Members( "ABC::Base" )       // inherits from ABC::Base
    {
        Double( Age ) := 0,      // additional members
    };
};

Print( ABC::Child().Greet(), "\n" );   // "Hola"
```

**Multiple inheritance is NOT supported.** Use Packages and `ImportPackages` instead.

### Pitfall: Changing Base Function Signatures

If you change a base class function's signature (e.g., add an argument), derived classes that override it **will break** at runtime unless they also update their signature. Use interfaces to catch this at lint time.

## Implementing Interfaces

```slang
TypeDefineInterface( "ABC::Drawable" )
{
    Draw = Func( Self ) Returns() { };
};

TypeDefine( "ABC::Circle" )
{
    Draw = Func( Self )
    Returns()
    {
        Printf( "Drawing circle with radius %d\n", Self.Radius );
    };

    Members()
    Implements( "ABC::Drawable" )
    {
        Double( Radius ) := 1,
    };
};
```

### Extending Interfaces

```slang
TypeDefineInterface( "ABC::A" )
{
    Func A = Func( Self ) Returns( String() ) { };
};

TypeDefineInterface( "ABC::B" )
{
    Func B = Func( Self ) Returns( String() ) { };
};

TypeDefineInterface( "ABC::AB" )
{
    Extends( "ABC::A", "ABC::B" )
};
```

## Importing Packages

```slang
TypeDefine( "ABC::My Widget" )
{
    Members()
    ImportPackages( "My Namespace::Logging" )
    {
        String( Name ) := "Widget",
    };
};

W = ABC::My Widget();
W.Log( "initialized" );   // [LOG] Widget: initialized
```

## Static Members

Static variables are shared across all instances. They can only be accessed via Lambdas:

```slang
TypeDefine( "ABC::Counter" )
{
    Count = 0;
    Increment = Lambda( Self ) Returns() { Count++; };
    Get Count = Lambda( Self ) Returns( Double() ) Return( Count );

    Members() {};
};

A = ABC::Counter();
B = ABC::Counter();
A.Increment();
A.Increment();
Print( B.Get Count(), "\n" );    // 2 (shared across instances)
```

## Reference Counting

Add `Double( _RefCount )` to enable pass-by-reference instead of copy-on-write:

```slang
TypeDefine( "ABC::Node" )
{
    Members()
    {
        Double( _RefCount ),
        String( Value ) := "",
        Any( Next )     := Null,
    };
};

A = ABC::Node( Value := "first" );
B = A;                    // B is a REFERENCE to A, not a copy
B.Value = "modified";
Print( A.Value, "\n" );  // "modified" (same object)
```

Without `_RefCount`, assignment creates a full copy.

## TypeForward (Forward Declarations)

Use when a type needs to reference itself (recursive types):

```slang
TypeForward( "ABC::Tree Node" );

TypeDefine( "ABC::Tree Node" )
{
    Members()
    {
        Double( _RefCount ),
        String( Data )  := "",
        Any( Left )     := Null,
        Any( Right )    := Null,
    };
};
```

## The Self Arg and Lambda Gotcha

`Self` is NOT a normal variable -- Lambdas cannot capture it in their closure:

```slang
// WRONG -- Self is not found when lambda executes
Create Bad Lambda = Func( Self )
Returns( Slang() )
{
    Return( Lambda() Self.Name );    // will error!
};

// CORRECT -- assign Self to a local variable first
Create Good Lambda = Func( Self )
Returns( Slang() )
{
    This = Self;
    Return( Lambda() This.Name );    // works
};
```

> **Note:** Without `_RefCount`, `This = Self` creates a **copy**. Changes to the original won't be reflected in the lambda's captured copy.

## Behavior Flags

Set `_Flags` inside the type definition:

```slang
TypeDefine( "ABC::Strict Type" )
{
    _Flags = TypedStructureFlag::Check Arguments
           | TypedStructureFlag::Sealed;

    Members()
    {
        Double( Value ) := 0,
    };
};
```

| Flag | Effect |
|------|--------|
| `TypedStructureFlag::Check Arguments` | Type-check member assignments at runtime. **Always use this unless there's a reason not to.** |
| `TypedStructureFlag::Sealed` | Prevents inheritance from this type |
| `TypedStructureFlag::Support Properties` | Enables property getter/setter pattern |

## Reflection

```slang
// Get type metadata
Info = TypeInfo( "ABC::My Type" );

// Convert instance to plain Structure
S = Structure( My Instance );

// Get component list
Components = @Typed Structure::Components( My Instance );
```

## Conversions

```slang
// Typed Structure -> Structure
S = Structure( ABC::Test() );

// Structure -> Typed Structure (via cast)
TS = @Typed Struct::Cast( ABC::Test(), My Structure );

// Clone
Clone = TypedStructureClone( Original );
```

## Practical Example: Linked List

```slang
TypeForward( "ABC::List Node" );

TypeDefine( "ABC::List Node" )
{
    /****************************************************************
    **  Routine: Append
    **
    **  Appends a new node with the given value to the end of the list.
    ****************************************************************/
    Append = Func( Self, String( Value ) )
    Returns()
    {
        If( TypeOf( Self.Next ) == "Null" )
        {
            Self.Next = ABC::List Node( Data := Value );
        }
        :
        {
            Self.Next.Append( Value );
        };
    };

    /****************************************************************
    **  Routine: To Array
    **
    **  Converts the list to an array of values.
    ****************************************************************/
    To Array = Func( Self )
    Returns( Array() )
    {
        Result = [ Self.Data ];
        If( TypeOf( Self.Next ) != "Null" )
        {
            Result = Result ++ Self.Next.To Array();
        };
        Return( Result );
    };

    Members()
    {
        Double( _RefCount ),
        String( Data ) := "",
        Any( Next )    := Null,
    };
};

// Usage
Head = ABC::List Node( Data := "A" );
Head.Append( "B" );
Head.Append( "C" );
Print( Head.To Array(), "\n" );   // [ "A", "B", "C" ]
```

## Quick Reference

| Task | Syntax |
|------|--------|
| Define type | `TypeDefine( "Scope::Name" ) { ... Members() { ... }; };` |
| Define streamable | `TypeDefineStreamable( ID, "Scope::Name" ) { ... };` |
| Define interface | `TypeDefineInterface( "Scope::Name" ) { ... };` |
| Define package | `TypeDefinePackage( "Scope::Name" ) { ... ContractMembers() { ... }; };` |
| Forward declare | `TypeForward( "Scope::Name" );` |
| Instantiate | `X = Scope::Name();` or `X = Scope::Name( Member := Value );` |
| Link | `Link( "_TYPE Script Name" );` |
| Inherit | `Members( "Base::Type" ) { ... };` |
| Implement | `Members() Implements( "Interface" ) { ... };` |
| Import package | `Members() ImportPackages( "Package" ) { ... };` |
| Ref counting | Add `Double( _RefCount )` to Members |
| Seal type | `_Flags = TypedStructureFlag::Sealed;` |
| Arg checking | `_Flags = TypedStructureFlag::Check Arguments;` |
| Reflection | `TypeInfo( "Scope::Name" )` |
| Convert to struct | `Structure( Instance )` |
| Clone | `TypedStructureClone( Instance )` |
