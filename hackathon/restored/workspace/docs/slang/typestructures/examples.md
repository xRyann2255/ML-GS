# Typed Structure Examples

Worked examples and exercises for learning Typed Structures in Slang. See `workingWithTypedStructures.md` for the full reference guide.

---

## Example: Basic Definition, Instantiation, and Type Checking

From `Example: Typed Structure 2` -- demonstrates defining types, creating instances, type checking, and cleanup with `TypeUndefine`.

```slang
TypeDefine( "Wing Info" )
{
    Members()
    {
        Array(  Table   ),      // Matrix of vol win data
        Array(  Headers ),      // Info for each col in Table
        Array(  Tags    ),      // Info for each row in Table
        String( Cross   ),      // Cross this Table is for
    };
};

TypeDefine( "CalcView" )
{
    Members()
    {
        Structure( EmptyValues ),   // Initial values
        Array(     Info        ),   // Array of CalcViewItems
        Structure( LabelToItem ),   // Struct to index info by Label
    };
};

TypeDefine( "Silly Example" )
{
    Members()
    {
        String( A String ) := "Something",
        Any(    Anything ) := 3.7,      // Can be any type
        Double( A Double ) := 1.0,
    };
};

// Print info for all defined types
ForEach( Type, TypeInfo() )
{
    Print( "========= ", Type, " ==========\n" );
    Print( TypeInfo( Type ), "\n" );
};

// Create and inspect an instance
Silly Value = Typed Structure( "Silly Example" );
Print( "====== Silly Value ======\n", Silly Value, "\n" );

// Assign an array to an Any member (works fine)
Silly Value.Anything = [ 3, 4 ];

// Type checking: assigning a String to a Double member should fail
If( Defined( Silly Value.A Double = "Foo" ) )
{
    Print( "*** Yikes!  Type checking is broken\n" );
}
:
{
    Print( "--> Type check error (correct):\n", LastError(), "\n" );
};

// Cannot undefine a type while instances exist
If( TypeUndefine( "Silly Example" ) )
{
    Print( "*** Yikes!  TypeUndefine checking is broken\n" );
}
:
{
    Print( "--> Illegal to undefine right now (correct):\n", LastError(), "\n" );
};

// Destroy the instance first, then undefine
Destroy( Silly Value );

If( TypeUndefine( "Silly Example" ) )
{
    Print( "--> 'Silly Example' type removed\n" );
}
:
{
    Print( "*** Yikes!  Can't TypeUndefine( Silly Example )\n", LastError(), "\n" );
};

// Clean up other types
TypeUndefine( "Wing Info" );
TypeUndefine( "CalcView" );
```

**Key lessons:**
- Members can be any data type, including `Any()` for flexible typing
- Type checking prevents assigning wrong types to typed members (e.g., String to Double)
- `TypeUndefine` only works when no live instances exist
- Always `Destroy` instances before undefining their type

---

## Exercise 1: Interfaces as Type Guarantees

**Task:** Write a function that accepts a typed structure, calls `Get Area` on it, and returns the square root. The input must be **guaranteed** to have a `Get Area` method.

**Solution:** Define an interface, implement it, and use the interface as the function's parameter type:

```slang
// 1. Define the interface contract
TypeDefineInterface( "ABC::Get Area" )
{
    Get Area = Func( Self ) Returns( Double() ) { };
};

// 2. Define a type that implements the interface
TypeDefine( "ABC::Test" )
{
    Get Area = Func( Self )
    Returns( Double() )
    {
        Return( 25 );
    };

    Members()
    Implements( "ABC::Get Area" );
};

// 3. The function uses the interface as its parameter type
//    This guarantees at parse-time that the input has Get Area
Private::Exercise 1 = Func(
    ABC::Get Area( Input ),
)
Returns( Double() )
{
    Return( Sqrt( Input.Get Area() ) );
};

Printf( "Square Root of Get Area() is %d\n", @Private::Exercise 1( ABC::Test() ) );
// Output: Square Root of Get Area() is 5
```

**Key lessons:**
- Interfaces define contracts -- they guarantee which methods are available
- Using an interface as a parameter type gives you compile/parse-time safety
- Any type that `Implements` the interface can be passed to the function

---

## Exercise 2: Sealed Types (Preventing Inheritance)

**Task:** Create a base class that **cannot** be inherited. Demonstrate the exception.

**Solution:** Use the `TypedStructureFlag::Sealed` flag:

```slang
TypeDefine( "ABC::Test" )
{
    _Flags = TypedStructureFlag::Support Properties
           | TypedStructureFlag::Check Arguments
           | TypedStructureFlag::Sealed;

    Get Area = Func( Self )
    Returns( Double() )
    {
        Return( 25 );
    };

    Members()
    {};
};

// This will throw an exception because ABC::Test is Sealed
AssertException(
    "Cannot inherited a Sealed Class",
    TypeDefine( "ABC::Test Inherit" )
    {
        Members( "ABC::Test" )
    }
);
```

**Key lessons:**
- `TypedStructureFlag::Sealed` prevents any type from inheriting
- Use this for types that should never be extended (final classes)
- Combining multiple flags with `|` (bitwise OR)

---

## Exercise 3: Properties (Getter/Setter Pattern)

**Task:** Create a typed structure with a `Foo` member and an automatic access counter that increments every time `Foo` is read or written.

**Solution:** Use `TypedStructureFlag::Support Properties` with getter/setter functions:

```slang
TypeDefine( "ABC::Test" )
{
    _Flags = TypedStructureFlag::Support Properties
           | TypedStructureFlag::Check Arguments;

    // Getter: called when reading .Foo
    Foo Getter = Func( Self )
    Returns( String() )
    {
        Self.p_Count Of Foo++;
        Return( Self.p_Foo );
    };

    // Setter: called when writing .Foo
    Foo Setter = Func( Self, String( New Value ) )
    Returns()
    {
        Self.p_Foo = New Value;
        Self.p_Count Of Foo++;
    };

    // Read-only property (getter only)
    Count Getter = Func( Self )
    Returns( Double() )
    {
        Return( Self.p_Count Of Foo );
    };

    Members()
    {
        String( p_Foo )          := "Foo",
        Double( p_Count Of Foo ) := 0,
    };
};

X = Apply( "ABC::Test" );
Printf( "Count is %d\n", X.Count );                           // Count is 0
Printf( "Read value of Foo: %s\n", X.Foo );                   // Read value of Foo: Foo
Printf( "Count is %d\n", X.Count );                           // Count is 1
Printf( "Write value of Foo: %s\n", ( X.Foo = "Foo New" ) );  // Write (implicit read too)
Printf( "Count is %d\n", X.Count );                           // Count is 3
```

**Key lessons:**
- `TypedStructureFlag::Support Properties` enables the getter/setter pattern
- Naming convention: `<PropertyName> Getter` and `<PropertyName> Setter`
- The underlying data members are prefixed with `p_` (private by convention)
- Writing triggers an implicit read, so the counter increments for both
- A property with only a Getter is effectively read-only

---

## Example Script Index

The following scripts in SecDb demonstrate various Typed Structure features. Load them with `Link( "ScriptName" )` or browse them in SecView.

| Script | Topics Covered |
|--------|---------------|
| `Example: TypeCase` | Using Typecase with typed structures |
| `Example: Typed Struct Package` | Defining and importing packages (mixins) |
| `Example: Typed Struct Property` | Property getter/setter pattern |
| `Example: Typed Struct Stream` | Streamable typed structures |
| `Example: Typed Structure` | Basic definition and usage |
| `Example: Typed Structure 2` | Type checking, TypeUndefine lifecycle |
| `Example: Typed Structure 3` | Additional patterns |
| `Example: Typed Structure 4` | Additional patterns |
| `Example: Typed Structure as DT` | Using typed structures as data types |
| `Example: Typed Structure BB` | Bloomberg integration example |
| `Example: Typed Structure Clone` | Cloning and deep-copy |
| `Example: Typed Structure Eqlty` | Equality comparison override |
| `Example: Typed Structure Inher` | Inheritance and `@_Super()` |
| `Example: Typed Structure MemFun` | Member functions |
| `Example: Typed Structure Msg` | Msg overrides (constructor, destructor) |
| `Example: Typed Structure Ops` | Operator overloading (`+`, `-`, `*`, etc.) |
| `Example: Typed Structure Ops1` | More operator overloading |
| `Example: Typed Structure Sealed` | Sealed types (preventing inheritance) |
| `Example: Typed Structures Pimpl` | Pointer-to-implementation pattern |

---

## See Also

- [workingWithTypedStructures.md](workingWithTypedStructures.md) -- full reference guide
- [commonFunctions.md](commonFunctions.md) -- quick function lookup
- `.github/structures/` -- plain Structure, StructureCase, GStructure
