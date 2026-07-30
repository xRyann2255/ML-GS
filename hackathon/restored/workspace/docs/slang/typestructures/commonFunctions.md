# Typed Structure Functions -- Quick Reference

A concise lookup of every built-in function related to Typed Structures. For detailed examples see `workingWithTypedStructures.md`.

---

## TypeDefine

**Define a non-streamable typed structure.**

```
TypeDefine( "Scope::Name" ) { ... Members() { ... }; };
```

- Scope and Name must differ.
- Members block must be last.

```slang
TypeDefine( "ABC::Point" )
{
    Members()
    {
        Double( X ) := 0,
        Double( Y ) := 0,
    };
};
```

---

## TypeDefineStreamable

**Define a streamable typed structure (can be serialized).**

```
TypeDefineStreamable( TypeID, "Scope::Name" ) { ... };
```

- `TypeID` must be a globally unique integer.
- Not recommended for database persistence -- use UFOs instead.

---

## TypeDefineInterface

**Define an interface contract.**

```
TypeDefineInterface( "Scope::Name" ) { FuncName = Func( Self ) Returns( ... ) { }; };
```

---

## TypeDefinePackage

**Define a reusable function package (mixin).**

```
TypeDefinePackage( "Scope::Name" ) { ... ContractMembers() { ... }; };
```

---

## TypeForward

**Forward-declare a type for recursive/circular definitions.**

```
TypeForward( "Scope::Name" )
```

```slang
TypeForward( "ABC::Tree" );
TypeDefine( "ABC::Tree" )
{
    Members()
    {
        Any( Left ) := Null,
        Any( Right ) := Null,
    };
};
```

---

## TypeInfo

**Get metadata about a type.**

```
TypeInfo( TypeName ) => Structure
```

```slang
Info = TypeInfo( "ABC::Point" );
Print( Info.NumInstances, "\n" );
```

---

## TypeInfoByID

**Get metadata about a type by its numeric ID.**

```
TypeInfoByID( TypeID ) => Structure
```

---

## TypeUndefine

**Remove a type definition (only when no instances exist).**

```
TypeUndefine( "Scope::Name" ) => Double (True/False)
```

---

## TypeLink

**Register a streamable typed structure globally.**

```
TypeLink( "Scope::Name" )
```

---

## Link (for Typed Structures)

**Link a non-streamable typed structure's defining script.**

```
Link( "_TYPE Script Name" )
```

```slang
Link( "_TYPE My Widget" );
W = My Namespace::My Widget();
```

---

## SmartLink (Dynamic Linking)

**Link a script at runtime when the name is only known dynamically.**

```
SmartLink( ScriptName )
```

```slang
SmartLink( "_TYPE " + Type Script Name );
Instance = Apply( Type Name );
```

---

## Members

**Declare typed data members inside a TypeDefine block.**

```
Members( [BaseType] ) [Implements(...)] [ImportPackages(...)] { ... };
```

| Syntax | Meaning |
|--------|---------|
| `Members() { ... }` | No base type |
| `Members( "Base::Type" ) { ... }` | Inherit from base |
| `Members() Implements( "IFace" ) { ... }` | Implement interface |
| `Members() ImportPackages( "Pkg" ) { ... }` | Import package |

---

## Msg New

**Constructor function -- called automatically on instantiation.**

```slang
Msg New = Func( Self )
Returns()
{
    // initialization logic
};
```

- **Only accepts `Self`** -- no extra arguments allowed.

---

## Instantiation

Three equivalent ways:

```slang
X = Scope::Name();                             // preferred
X = Typed Structure( "Scope::Name" );          // by string
X = Apply( "Scope::Name" );                    // dynamic
X = Scope::Name( Member := Value );            // with member init
```

---

## TypedStructureClone

**Deep-clone a typed structure instance.**

```
TypedStructureClone( Instance ) => Typed Structure
```

```slang
Copy = TypedStructureClone( Original );
```

---

## Behavior Flags

Set via `_Flags` inside the type definition:

| Flag | Effect |
|------|--------|
| `TypedStructureFlag::Check Arguments` | Runtime type-checking on member assignments |
| `TypedStructureFlag::Sealed` | Prevents inheritance |
| `TypedStructureFlag::Support Properties` | Enables getter/setter properties |

```slang
_Flags = TypedStructureFlag::Check Arguments | TypedStructureFlag::Sealed;
```

---

## Reference Counting

Add `Double( _RefCount )` to Members to enable pass-by-reference:

```slang
Members()
{
    Double( _RefCount ),
    String( Data ) := "",
};
```

Without this, typed structures are copied on assignment.

---

## Conversion Functions

| Task | Function |
|------|----------|
| To Structure | `Structure( Instance )` |
| Get components | `@Typed Structure::Components( Instance )` |
| Cast from Structure | `@Typed Struct::Cast( TypeInstance, SourceStruct )` |
| Clone | `TypedStructureClone( Instance )` |
| Deep clone | `@DataType::Deep Clone( Instance )` (requires `Link( "_Lib Datatype Cloning Fns" )`) |

---

## See Also

- [workingWithTypedStructures.md](workingWithTypedStructures.md) -- full guide with patterns
- `.github/structures/` -- plain Structure, StructureCase, GStructure
- `.github/builtins.md` -- complete built-in function reference
