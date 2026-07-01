# Structure Core Functionality -- Quick Reference

A concise lookup of every **built-in** structure function in Slang (no `Link()` required). For **library** functions (requiring `Link( "_LIB Structure Functions" )`), see `structureFunctions.md`. For detailed examples see `examples.md`; for a conceptual walkthrough see `workingWithStructures.md`.

---

## ForComponent

**Iterate over all keys in a structure (alphabetical order).**

```
ForComponent( Key, Container ) { ... }
```

```slang
S = {| "B" := 2, "A" := 1 |};
ForComponent( Key, S )
{
    Print( Key, " = ", S[ Key ], "\n" );
};
// Output: A = 1, B = 2
```

---

## ForComponentValue

**Iterate over keys and values together.**

```
ForComponentValue( Key, Value, Container ) { ... }
ForComponentValue( Key, &Value, Container ) { ... }   // modifiable
```

```slang
ForComponentValue( K, V, {| "X" := 10, "Y" := 20 |} )
{
    Print( K, " => ", V, "\n" );
};
```

---

## ComponentExists

**Check if a key exists (case-insensitive for Structure).**

```
ComponentExists( Container, Tag ) => Double (True/False)
```

```slang
ComponentExists( {| "Name" := "Alice" |}, "name" );   // True
ComponentExists( {| "Name" := "Alice" |}, "Age" );    // False
```

---

## ComponentExistsStrict

**Like ComponentExists but redboxes if Container is not a valid container type.**

```
ComponentExistsStrict( Container, Tag ) => Double (True/False)
```

---

## ComponentTestAndGet

**Get a value by key, with a True/False return indicating success.**

```
ComponentTestAndGet( Container, Tag, ValueVar ) => Double (True/False)
```

- If key exists: returns `True`, stores value in `ValueVar`.
- If key missing: returns `False`, `ValueVar` unchanged.

```slang
If( ComponentTestAndGet( Config, "Timeout", Val ) )
{
    Print( "Timeout = ", Val, "\n" );
};
```

---

## ComponentGetStrict

**Like ComponentTestAndGet but redboxes if Container is invalid.**

```
ComponentGetStrict( Container, Tag, ValueVar ) => Double (True/False)
```

---

## ComponentExtract

**Get a value by key, with a default fallback.**

```
ComponentExtract( Container, Tag, DefaultValue ) => Any
```

```slang
Timeout = ComponentExtract( Config, "Timeout", 30 );
// Returns Config.Timeout if it exists, else 30
```

---

## ComponentExtractStrict

**Like ComponentExtract but redboxes if Container is invalid.**

```
ComponentExtractStrict( Container, Tag, DefaultValue ) => Any
```

---

## ComponentEnsure

**Get or create a key with an initial value.**

```
ComponentEnsure( Container, Key, InitialValue ) => LValue
```

If key exists, returns its value. If missing, creates it with `InitialValue` and returns that.

```slang
Count = ComponentEnsure( Totals, "Errors", 0 );
Totals.Errors += 1;
```

---

## ComponentReplace

**Replace the value of a key.**

```
ComponentReplace( Container, Key, Value ) => Any
```

```slang
ComponentReplace( Config, "Timeout", 60 );
```

---

## Structure (Constructor)

**Create a Structure with optional inline key-value pairs.**

```
Structure() => Structure
Structure( Key1, Value1, Key2, Value2, ... ) => Structure
```

```slang
S = Structure( "Name", "Alice", "Age", 30 );
```

---

## StructureFromKeys

**Create a Structure from parallel arrays.**

```
StructureFromKeys( Keys, Values [, CastToStringKeys] ) => Structure
```

```slang
S = StructureFromKeys( [ "A", "B" ], [ 1, 2 ] );
```

---

## GStructureFromKeys

**Create a GStructure from parallel arrays (preserves insertion order).**

```
GStructureFromKeys( Keys, Values ) => GStructure
```

---

## StructureUnion

**Merge one structure into another in place.**

```
StructureUnion( Target, Source ) => (modifies Target)
```

Adds keys from `Source` that are missing in `Target`. Does not overwrite existing keys.

```slang
S1 = {| "A" := 1 |};
StructureUnion( S1, {| "A" := 99, "B" := 2 |} );
// S1 = {| "A" := 1, "B" := 2 |}
```

---

## StructureStatistics

**Get memory and usage statistics for a structure.**

```
StructureStatistics( Structure ) => Structure
```

```slang
Stats = StructureStatistics( My Struct );
Print( Stats.KeyCount, " keys\n" );
```

---

## Destroy (on Structure Keys)

**Remove a key from a structure.**

```slang
S = {| "A" := 1, "B" := 2, "C" := 3 |};
Destroy( S.B );
// S = {| "A" := 1, "C" := 3 |}
```

---

## Member Functions

| Method | Description |
|--------|-------------|
| `S.Keys()` | Returns sorted array of keys |
| `S.Values()` | Returns array of values (in key-sorted order) |
| `S.UnsortedKeys()` | Returns keys in insertion order |

---

## Structure::keys

**Get the sorted keys of a Structure as an array.**

```
Structure::keys( Structure ) => Array
```

Called as a member function on a Structure instance.

```slang
S = {| "B" := 2, "A" := 1 |};
Print( S.Keys(), "\n" );                    // [ "A", "B" ]
```

---

## Structure::values

**Get the values of a Structure as an array (in key-sorted order).**

```
Structure::values( Structure ) => Array
```

```slang
S = {| "B" := 2, "A" := 1 |};
Print( S.Values(), "\n" );                  // [ 1, 2 ]
```

---

## Structure::unsortedkeys

**Get the keys of a Structure in insertion order.**

```
Structure::unsortedkeys( Structure ) => Array
```

```slang
S = {| "B" := 2, "A" := 1 |};
Print( S.UnsortedKeys(), "\n" );            // [ "B", "A" ]
```

---

## Operators Summary

| Operator | Description |
|----------|-------------|
| `S1 ++ S2` | Merge; left-hand values win for duplicate keys |
| `S1 + S2` | Element-wise addition (numeric values) |
| `S1 - S2` | Element-wise subtraction |
| `S1 * S2` | Element-wise multiplication |
| `S1 / S2` | Element-wise division |
| `S + Scalar` | Add scalar to each value |
| `S == S2` | Deep equality comparison |
| `S != S2` | Deep inequality comparison |
| `+=`, `-=`, `*=`, `/=` | In-place arithmetic |

---

## See Also

- [workingWithStructures.md](workingWithStructures.md) -- full guide with patterns
- `.github/typestructures/` -- typed structures (object-like types with member functions)
- `.github/builtins.md` -- complete built-in function reference
