# Structure Library Functions (`_LIB Structure Functions`)

Functions in this file require:

```slang
Link( "_LIB Structure Functions" );
```

All functions are called with the `@Structure::` prefix unless otherwise noted.

> **Note:** This file documents the **library** functions from `_LIB Structure Functions`.
> For **built-in** structure operations (`ForComponent`, `ForComponentValue`, `ComponentExists`,
> `ComponentTestAndGet`, `ComponentExtract`, `StructureUnion`, `Destroy`, etc.) see
> `core-functionality.md` in this folder.

---

## Table of Contents

| Category | Functions | Source |
|----------|-----------|--------|
| **Flatten / Reshape / Unflatten** | Flatten, Unflatten, Reshape, Depth Flatten, Depth Flatten To Table, To Array of Array | Lib 1 |
| **Set Operations** | Intersection, Intersection With Contents, UnionSimple, Right Union, Combine | Lib 1 |
| **Inversion** | Invert, InvertSimple, InvertSingletons, InvertToGStructure, Invert Structure Of Structures, StructureCase::InvertSimple | Lib 1 |
| **Merging** | MergeSimple, Merge Deep | Lib 1 |
| **Extraction / Filtering** | ExtractSimple, Extract, Filter, FilterSimple | Lib 1 |
| **Conversion (Array <-> Struct)** | ArrayOfStructToStruct, ArrayOfStructToStructWMTags, ArrayOfStructToStructOfArray, StructOfArrayToArrayOfStruct, StructOfArrayToArrayOfStructUneq, StructToArrayOfStruct, ArrayOfStructToArrayOfArray, StructureCaseToStructure, SingletonStructsToStruct, StructToSingletonStructs, CastToStructure | Lib 1 |
| **Diff / Comparison** | Diff, AllDiffs, Diff Symmetric, Compare to Depth, Det Diff In Arrays Of Structs | Lib 1 |
| **Deep Entry / Path Access** | Add Deep Entry, Entry, IsLeaf | Lib 1 |
| **Iteration / Map / Fold** | ForEachKeyVal, KeyVal Mapcar, KeyVal Foldl, KeyApply, ValApply, Map, SMap | Lib 1 |
| **Fold / Unfold Array Leaves** | Fold In Array Leaves, Unfold Array Leaves | Lib 1 |
| **Pruning / Reset** | PruneZero, ResetValues | Lib 1 |
| **Display / Printing** | Print Simple, As Single Line String | Lib 1 |
| **Querying** | ArrayOfTags, All Keys | Lib 1 |
| **Validation / Depth** | Validate Structure, Validate Depth, Ensure Min Depth, Enforce Depth, Relax Depth | Lib 2 |
| **Path Access (Get / Set / Destroy)** | Set By Path, Get By Path, Get By Path Deep, Get By Uri Path, Destroy By Path | Lib 2 |
| **Sorting** | Sorted by Values, Sorted by Keys, Sorted by Values Deep, Sort From Deep | Lib 2/3 |
| **Renaming** | Rename Components, Rename Components Single, Rename Components By Path, KeyRename InPlace | Lib 2 |
| **Leaf / Key Traversal** | Apply to Leaves, Transform Leaves, Apply to Keys, Get Leaves, Get Leaf Keys, Get Leaf Keys and Values | Lib 2/3 |
| **Union / Intersect (Extended)** | Union, Struct Union, Union upto Level, Union Deep, StrictUnion, Intersect, Copy Common Values, Intersection with Values, Keys Intersection | Lib 2/3 |
| **Grouping / Categorizing** | Group By, Categorize, Categorize As Tree, Aggregate Structure | Lib 2/3 |
| **Aggregation** | Aggregate, Max, Min, Sum | Lib 2 |
| **Diff (Lossless)** | DiffLossless, DiffLossless Apply, DiffLossless Invert, DiffLossless Flatten, DiffLossless Flatten Apply, DiffLossless Conflicts | Lib 3 |
| **Diff (Reporting)** | DiffReport, Minus, Cmp Structures, Diff Symmetric Flatten | Lib 2 |
| **Cross Product / Cartesian** | Cross Array of Struct, Cross Struct of Array, Cross Product, Cartesian Product | Lib 2/3 |
| **Conversion (Extended)** | StructOfStructToArrayOfStruct, StructOfStructToArrayOfArray, CVStructOfCVStructToArrayOfArray, From Array Of Array, StructOfArrayToArrayOfStructMany, From GStructure, ArrayOfStructToStructNested, ArrayOfStructToArrayOfStructCase, ArrayToArrayOfStruct, TableInit, FromKeysWithDuplicates | Lib 2/3 |
| **Filtering (Extended)** | Filter Dimensions, Filter Out Dimensions, Filter At Level, Match Keys, Grep, Extract Value, Extract Values as Array | Lib 2 |
| **Path Querying** | Get All Paths, Get All Paths To Value, Get All Paths with Filter, Find All Paths For Key, Find Overrides All, Find And Replace All, Max Depth | Lib 2/3 |
| **Misc Utilities** | One Liner, Map Of, Is Subset Of, Compose, DotProduct, Differentiate, Bucket, Contains, Component Exists Deep, Truncate Structure, Partially Structure Table, Redimension, Redimension Fast, Recursive Redim, Sum Structure Leaf, Extreme Element, Most Frequent Elements, Sprintf, Extend, Project, KeyValApply InPlace, Apply At Level, Apply At Level InPlace, Replace Leaves or Keys with, Iterate Deep, Get Keys, Get All Keys, Build Parents Tree, Sample, Summarise Strings, ArrayToGStructure, Common Values | Lib 2/3 |

---

## Flatten / Reshape / Unflatten

---

### Structure::Flatten

**Convert a multi-level structure to a single level by concatenating keys with a delimiter.**

```
Structure::Flatten = Func(
    Any( X ),                                       // Structure, StructureCase, or Array to flatten
    String( Delimiter )             := ".",          // Key concatenation delimiter
    String( Convert To Type )       := "",           // Optional output type (e.g. "StructureCase")
    Double( Flatten Any Structure ) := False,        // Also flatten Typed Structures
    Double( Flatten Arrays )        := False,        // Also flatten arrays (indices become string keys)
    Double( Levels to Flatten )     := -1,           // -1 = all levels; positive = max levels
    Double( All Lowercase )         := False,        // Lowercase all keys (use with StructureCase output)
)
Returns( Any() )
```

Preserves input type unless `Convert To Type` is set. Returns input as-is for non-structure types.

```slang
// Basic flatten
S = {| "A" := {| "B" := 1, "C" := 2 |}, "D" := 3 |};
Flat = @Structure::Flatten( S );
// Result: {| "A.B" := 1, "A.C" := 2, "D" := 3 |}

// Custom delimiter
Flat2 = @Structure::Flatten( S, Delimiter := "_" );
// Result: {| "A_B" := 1, "A_C" := 2, "D" := 3 |}

// Flatten arrays too
S2 = {| "X" := [ "a", "b" ] |};
Flat3 = @Structure::Flatten( S2, Flatten Arrays := True );
// Result: {| "X.0" := "a", "X.1" := "b" |}

// Flatten only 1 level
Deep = {| "A" := {| "B" := {| "C" := 1 |} |} |};
Flat4 = @Structure::Flatten( Deep, Levels To Flatten := 1 );
// Result: {| "A.B" := {| "C" := 1 |} |}
```

See also: `Structure::Reshape`, `Structure::Unflatten`.

---

### Structure::Unflatten

**Reconstructs a nested structure from a flattened one. Inverse of `Flatten`.**

```
Structure::Unflatten = Func(
    GrowableStringValueStructure( S ),   // Flattened Structure or StructureCase
    String( Delimiter )   := ".",        // Must match the delimiter used during Flatten
)
Returns( StringValueStructure() )
```

Throws if conflicting keys exist (e.g. both `"a"` and `"a.b"` as keys).

```slang
Flat = {| "a" := 1, "b.c" := 2, "b.d" := 3 |};
Nested = @Structure::Unflatten( Flat );
// Result: {| "a" := 1, "b" := {| "c" := 2, "d" := 3 |} |}

// Custom delimiter
Flat2 = {| "a" := 1, "b_c" := 2, "b_d" := 3 |};
Nested2 = @Structure::Unflatten( Flat2, Delimiter := "_" );
// Result: {| "a" := 1, "b" := {| "c" := 2, "d" := 3 |} |}
```

---

### Structure::Reshape

**Reconstructs a nested structure from a flattened one. Similar to `Unflatten` but works with existing structures.**

```
Structure::Reshape = Func(
    FlatHead,                                       // Flattened Structure or StructureCase
    String( Delimiter ) := ".",
    Double( Allow Empty String As Key ) := False,   // Allow "" as a key segment
)
Returns( Any() )
```

```slang
Flat = {| "a" := 1, "b.c" := 2 |};
Reshaped = @Structure::Reshape( Flat );
// Result: {| "a" := 1, "b" := {| "c" := 2 |} |}
```

---

### Structure::Depth Flatten

**Like `Flatten`, but only flattens levels below the given depth.**

```
Structure::Depth Flatten = Func(
    X,                              // Input structure
    Double( Below Depth ),          // Levels to preserve before flattening
    String( Delimiter ) = ".",
)
Returns( Any() )
```

```slang
S = {| "A" := {| "B" := {| "C" := 1, "D" := 2 |} |} |};
// Depth 0: flatten everything (same as Flatten)
// Depth 1: preserve first level, flatten below
Result = @Structure::Depth Flatten( S, 1 );
// Result: {| "A" := {| "B.C" := 1, "B.D" := 2 |} |}
```

---

### Structure::Depth Flatten To Table

**Converts a deep structure into an array of structures (table) by treating the first N levels as fixed heading columns.**

```
Structure::Depth Flatten To Table = Func(
    X,                              // Deep structure
    Array( Fixed Heading Names ),   // Column names for the outer levels
    String( Delimiter ) = ".",
)
Returns( Array() )
```

```slang
Deep = {| "x" := {| "y" := 2, "z" := 3 |} |};
Table = @Structure::Depth Flatten To Table( Deep, [ "a" ] );
// Result: [ {| a := "x", y := 2, z := 3 |} ]
```

---

### Structure::To Array of Array

**Converts a multilevel structure to an array of arrays. Useful for pivot tables.**

```
Structure::To Array of Array = Func(
    X,                                              // Structure input
    Decompose Array = False,                        // pos arg: also decompose arrays
    Decompose Keys = False,                         // pos arg: decompose composite keys
    Double( Include Empty Paths ) := False,         // Include entries for empty sub-structures
)
Returns( Any() )
```

```slang
S = {| "A" := {| "B" := 1, "C" := 2 |}, "D" := {| "E" := 3 |} |};
AOA = @Structure::To Array of Array( S );
// Result: [ [ "A", "B", 1 ], [ "A", "C", 2 ], [ "D", "E", 3 ] ]

// With empty paths
S2 = {| "A" := {| |} |};
AOA2 = @Structure::To Array of Array( S2, Include Empty Paths := True );
// Result: [ [ "A", {||} ] ]
// Without Include Empty Paths: []
```

---

## Set Operations

---

### Structure::Intersection

**Returns the structure of keys common to two structures (recursive). Values are discarded (set to Null at leaf).**

```
Structure::Intersection = Func(
    Any( StructX ),     // Structure, StructureCase, or GStructure
    Any( StructY ),     // Must be same type as StructX
)
Returns( ComponentValueStructure(), Null )
```

Returns `Null` if types don't match.

```slang
A = {| "X" := 1, "Y" := 2, "Z" := 3 |};
B = {| "Y" := 10, "Z" := 20, "W" := 30 |};
Result = @Structure::Intersection( A, B );
// Result: {| "Y" := Null, "Z" := Null |}
```

---

### Structure::Intersection With Contents

**Like `Intersection`, but returns the values from the first structure.**

```
Structure::Intersection With Contents = Func(
    Structure( StructX ),
    Structure( StructY ),
)
Returns( Structure() )
```

```slang
A = {| "X" := 1, "Y" := 2 |};
B = {| "Y" := 99, "Z" := 3 |};
Result = @Structure::Intersection With Contents( A, B );
// Result: {| "Y" := 2 |}
```

---

### Structure::UnionSimple

**Adds keys from StructY to StructX if not already present. Non-recursive. Modifies StructX in place if passed by reference.**

```
Structure::UnionSimple = Func(
    StructX,        // ComponentValueStructure (modified in place if &)
    StructY,        // ComponentValueStructure
)
Returns( GStructure(), StringValueStructure(), Null )
```

```slang
A = {| "X" := 1 |};
B = {| "X" := 99, "Y" := 2 |};
@Structure::UnionSimple( A, B );
// A is now: {| "X" := 1, "Y" := 2 |}  (X kept from A, Y added from B)
```

---

### Structure::Right Union

**Copies Y on top of X (values from Y win). Returns new value.**

```
Structure::Right Union = Func(
    Any( X ),
    Any( Y ),
    Double( Recurse ) := False,     // If True, recursively merge nested structures
)
Returns( Any() )
```

```slang
X = {| "A" := 1, "B" := 2 |};
Y = {| "B" := 99, "C" := 3 |};
Result = @Structure::Right Union( X, Y );
// Result: {| "A" := 1, "B" := 99, "C" := 3 |}
```

---

### Structure::Combine

**General combining function. Applies one of three user-provided functions depending on whether a key is in A only, B only, or both.**

```
Structure::Combine = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
    Slang( Gen Value for key in A Only ),           // Func( key, Value A )
    Slang( Gen Value for key in B Only ),           // Func( key, Value B )
    Slang( Gen Value for key in both A and B ),     // Func( key, Value A, Value B )
)
Returns( ComponentValueStructure() )
```

A and B must be the same type. If a function returns `Null`, that key is excluded from the result.

```slang
A = {| "X" := 1, "Y" := 2 |};
B = {| "Y" := 20, "Z" := 3 |};

// Custom intersection: keep A values for common keys
Result = @Structure::Combine( A, B,
    \_,_a    -> Null,       // A only: exclude
    \_,_b    -> Null,       // B only: exclude
    \_,a,_b  -> a           // both: keep A's value
);
// Result: {| "Y" := 2 |}
```

---

## Inversion

---

### Structure::Invert

**Inverts a structure (values become keys, keys become values).**

```
Structure::Invert = Func(
    Struct,                                 // Structure, StructureCase, or GStructure
    Double( One to One )    := False,       // If True, throws on duplicate values
    Double( Ignore Duplicates ) := False,   // If True + One to One, silently picks first
)
Returns( Structure(), StructureCase(), GStructure(), Null )
```

By default (not One to One), values are arrays to support one-to-many mappings.

```slang
S = {| "a" := 1, "b" := 2, "c" := 3 |};

// Default: values are arrays
Inv = @Structure::Invert( S );
// Result: {| "1" := [ "a" ], "2" := [ "b" ], "3" := [ "c" ] |}

// One to One: values are scalars
Inv2 = @Structure::Invert( S, One to One := True );
// Result: {| "1" := "a", "2" := "b", "3" := "c" |}
```

---

### Structure::InvertSimple

**Simple inversion -- last value wins on duplicates. Values are cast to strings for keys.**

```
Structure::InvertSimple = Func(
    ComponentValueStructure( Struct ),
)
Returns( ComponentValueStructure(), Null )
```

```slang
S = {| "hello" := "world", "number" := 123 |};
Inv = @Structure::InvertSimple( S );
// Result: {| "world" := "hello", "123" := "number" |}
```

---

### Structure::InvertSingletons

**Inverts a structure, setting duplicate-value entries to Null.**

```
Structure::InvertSingletons = Func(
    Any( Struct ),
)
Returns( Structure(), Null )
```

---

### Structure::InvertToGStructure

**Inverts to a GStructure (keys can be non-string types).**

```
Structure::InvertToGStructure = Func( DT )
Returns( GStructure() )
```

---

### Structure::Invert Structure Of Structures

**Inverts a structure whose values are also structures. This inversion is reversible.**

```
Structure::Invert Structure Of Structures = Func(
    ComponentValueStructure( Struct ),
)
Returns( ComponentValueStructure() )
```

```slang
X = {| "a" := {| "x" := 1, "y" := 2 |}, "b" := {| "x" := 10, "z" := 20 |} |};
Y = @Structure::Invert Structure Of Structures( X );
// Y == {| "x" := {| "a" := 1, "b" := 10 |}, "y" := {| "a" := 2 |}, "z" := {| "b" := 20 |} |}
// Reversible: @Structure::Invert Structure Of Structures( Y ) == X
```

---

### StructureCase::InvertSimple

**Inverts a StructureCase (case-sensitive). Elements must be single strings.**

```
StructureCase::InvertSimple = Func(
    StructureCase( Struct ),
)
Returns( StructureCase() )
```

---

## Merging

---

### Structure::MergeSimple

**Recursively merges Y into X (in place). Non-structure values from Y overwrite X.**

```
Structure::MergeSimple = Func(
    &X,         // Structure passed by reference
    &Y,         // Structure to merge in
)
Returns()
```

```slang
X = {| "A" := {| "B" := 1 |}, "C" := 2 |};
Y = {| "A" := {| "D" := 3 |}, "C" := 99 |};
@Structure::MergeSimple( &X, &Y );
// X == {| "A" := {| "B" := 1, "D" := 3 |}, "C" := 99 |}
```

---

### Structure::Merge Deep

**Deep merge with a user-supplied merge function for type-matched values.**

```
Structure::Merge Deep = Func(
    ComponentValueStructure( &Left ),       // Modified in place
    ComponentValueStructure( Right ),
    Slang( Merge Func ),                    // Func( Left Val, Right Val, Merge Func ) -> merged value
)
Returns()
```

Throws on type mismatch between corresponding values.

---

## Extraction / Filtering

---

### Structure::ExtractSimple

**Extract a subset of keys from a structure. Ignores missing keys by default.**

```
Structure::ExtractSimple = Func(
    Any( Struc ),                       // Structure, StructureCase, GStructure, or Typed Structure
    Array( Keys ),                      // Keys to extract
    String( Return Type ) := TypeOf( Struc ),   // Override output type
    Double( Strict ) := False,          // If True, throw on missing keys
)
Returns( Any() )
```

```slang
S = {| "a" := 1, "b" := 2, "c" := 3 |};
Sub = @Structure::ExtractSimple( S, [ "a", "c" ] );
// Result: {| "a" := 1, "c" := 3 |}

// Strict mode
@Structure::ExtractSimple( S, [ "a", "z" ], Strict := True );
// Throws: "Could not extract 'z'..."
```

---

### Structure::Extract

**Extract keys from a structure or array of structures. Destructive on the source if passed by reference.**

```
Structure::Extract = Func(
    Struct,                             // Structure or Array of Structures
    TagsToExtract,                      // Array, String, Structure, or TypeSlice of keys
    StripTag = 0,                       // pos arg: if 1 and single tag, return value directly
    Default Value = NULL,               // pos arg: default for missing tags (only used if non-Null)
)
Returns( Any() )
```

```slang
S = {| "A" := 1, "B" := 2, "C" := 3 |};
Extracted = @Structure::Extract( S, [ "B", "C" ] );
// Result: {| "B" := 2, "C" := 3 |}

// With default value for missing keys
Extracted2 = @Structure::Extract( S, [ "B", "C", "D" ], 0, 0 );
// Result: {| "B" := 2, "C" := 3, "D" := 0 |}
```

---

### Structure::Filter

**Filter a structure by keys, values, or key+value pairs. Supports recursion.**

```
Structure::Filter = Func(
    Any( Struc ),
    Slang( FilterFunc ) = Slang(),                  // Filtering function
    Double( Filter by Leaves )  := False,           // Recurse into sub-structures
    Double( Filter by Keys )    := False,           // FilterFunc receives key
    Double( Filter by Keys And Values ) := False,   // FilterFunc receives (key, value)
    Double( Keep Empty Leaves ) := True,            // Keep empty sub-structs after filtering
    Slang( Filter Intermediate Func ) := Slang(),   // Applied to intermediate (branch) keys
)
Returns( Any() )
```

Default (no flags): `FilterFunc( value )` -- filter by value truthiness.

```slang
S = {| "A" := 1, "B" := 0, "C" := 3 |};

// Filter by value (truthy)
Result = @Structure::Filter( S );
// Result: {| "A" := 1, "C" := 3 |}

// Filter by key
Result2 = @Structure::Filter( S, \k -> k != "B", Filter by Keys := True );
// Result: {| "A" := 1, "C" := 3 |}

// Filter by key and value
Result3 = @Structure::Filter( S, \k, v -> k != "A" && v > 0, Filter by Keys And Values := True );
// Result: {| "C" := 3 |}
```

Prefer `FilterSimple` if you don't need recursion.

---

### Structure::FilterSimple

**Like `Filter` but without recursion. Faster for single-level structures.**

```
Structure::FilterSimple = Func(
    Any( Struc ),
    Slang( FilterFunc ) = Slang(),
    Double( Filter by Keys ) := False,
    Double( Filter by Keys And Values ) := False,
)
Returns( Any() )
```

---

## Conversion (Array <-> Struct)

---

### Structure::ArrayOfStructToStruct

**Converts an array of structures to a structure keyed by a named tag from each element.**

```
Structure::ArrayOfStructToStruct = Func(
    ArrayOfStruct,                              // Array of Structures
    TagName,                                    // Key name to extract as structure key
    SkipNoTags = False,                         // pos arg: skip elements missing TagName
    Error On Redefined Lines = False,           // pos arg: throw on duplicate keys
    RemoveTag := TRUE,                          // Remove TagName from stored values
    Double( Multiple Tags ) := False,           // Values become arrays (collect duplicates)
    Double( TagCaseSensitive ) := False,        // Return StructureCase
    Double( GStructure ) := False,              // Return GStructure (keys not stringified)
    Double( GCurve ) := False,                  // Return GCurve (keys must be Dates)
)
Returns( Structure(), NULL, Double(), StructureCase(), GStructure(), GCurve() )
```

```slang
Table = [
    {| "Key" := "The",   "Value" := "quick" |},
    {| "Key" := "Jumps", "Value" := "over" |},
];
Result = @Structure::ArrayOfStructToStruct( Table, "Key" );
// Result: {| "The" := {| "Value" := "quick" |}, "Jumps" := {| "Value" := "over" |} |}
```

---

### Structure::ArrayOfStructToStructWMTags

**Like `ArrayOfStructToStruct` but concatenates multiple tag names as the key.**

```
Structure::ArrayOfStructToStructWMTags = Func(
    Any( ArrayOfStruct ),
    Array( TagNames ),                              // Array of tag names to concatenate
    Double( SkipNoTags )                 = FALSE,   // pos arg
    Double( Error On Redefined Lines )   = FALSE,   // pos arg
    Double( RemoveTag )                 := TRUE,
    Double( Multiple Tags )             := False,
    Double( TagCaseSensitive )          := False,
)
Returns( Structure(), NULL, Double(), StructureCase() )
```

```slang
Data = [
    {| "First" := "A1", "Last" := "B1", "Count" := 1 |},
    {| "First" := "A2", "Last" := "B2", "Count" := 2 |},
];
Result = @Structure::ArrayOfStructToStructWMTags( Data, [ "First", "Last" ] );
// Result: {| "A1 B1" := {| "Count" := 1 |}, "A2 B2" := {| "Count" := 2 |} |}
```

---

### Structure::ArrayOfStructToStructOfArray

**Pivots an array of structures into a structure of arrays (column-oriented).**

```
Structure::ArrayOfStructToStructOfArray = Func(
    Array( ArrayOfStruct ),
    Double( Validation )       := False,    // Throw if keys are inconsistent
    Double( Union )            := False,    // Include tags not in first element
    Double( Union Incl Nulls ) := False,    // Like Union but pads with nulls
    Any( Null Replacement Value ) := Null,  // Replacement for missing components
)
Returns( Structure(), StructureCase(), GStructure(), NULL )
```

```slang
Data = [
    {| "Name" := "Alice", "Age" := 30 |},
    {| "Name" := "Bob",   "Age" := 25 |},
];
Result = @Structure::ArrayOfStructToStructOfArray( Data );
// Result: {| "Name" := [ "Alice", "Bob" ], "Age" := [ 30, 25 ] |}
```

---

### Structure::StructOfArrayToArrayOfStruct

**Inverse of `ArrayOfStructToStructOfArray`. All arrays must be the same size.**

```
Structure::StructOfArrayToArrayOfStruct = Func(
    Any( Struct Of Array ),     // Structure or GStructure; values must be equal-size arrays
)
Returns( Array(), Error() )
```

```slang
S = {| "a" := [ 1, 2 ], "b" := [ 3, 4 ] |};
Result = @Structure::StructOfArrayToArrayOfStruct( S );
// Result: [ {| "a" := 1, "b" := 3 |}, {| "a" := 2, "b" := 4 |} ]
```

---

### Structure::StructOfArrayToArrayOfStructUneq

**Like `StructOfArrayToArrayOfStruct` but allows arrays of different sizes (pads shorter ones).**

```
Structure::StructOfArrayToArrayOfStructUneq = Func(
    Any( Struct Of Array ),
)
Returns( Array(), Error() )
```

---

### Structure::StructToArrayOfStruct

**Converts a structure to an array of key-value pair structures.**

```
Structure::StructToArrayOfStruct = Func(
    ComponentValueStructure( Struct ),
    String( KeyTag )   = "Keys",            // pos arg: name for key field
    String( ValueTag ) = "Values",          // pos arg: name for value field
    String( ToType )   = "String",          // pos arg: type to cast keys to
    Double( Use StructureCase ) := False,
)
Returns( Array() )
```

```slang
S = {| "Foo1" := [ 1, 2, 3 ], "Foo2" := [ "A", "B" ] |};
Result = @Structure::StructToArrayOfStruct( S, "Key", "Value" );
// Result: [ {| "Key" := "Foo1", "Value" := [ 1, 2, 3 ] |}, {| "Key" := "Foo2", "Value" := [ "A", "B" ] |} ]
```

---

### Structure::ArrayOfStructToArrayOfArray

**Extracts specified keys from each structure in an array, returning an array of arrays.**

```
Structure::ArrayOfStructToArrayOfArray = Func(
    Array( Rows ),      // Array of structures
    Array( Keys ),      // Keys to extract (in order)
)
Returns( Array() )
```

---

### Structure::StructureCaseToStructure

**Deep-converts a StructureCase (and nested StructureCases) to Structure.**

```
Structure::StructureCaseToStructure = Func(
    inStruct,
)
Returns( Structure() )
```

```slang
SC = StructureCase( "Alpha", 99, "Bravo", [ StructureCase( "Charlie", 2 ) ] );
Result = @Structure::StructureCaseToStructure( SC );
// Result: Structure( "Alpha", 99, "Bravo", [ Structure( "Charlie", 2 ) ] )
```

---

### Structure::SingletonStructsToStruct

**Unions an array of structures into one (last value wins for duplicate keys).**

```
Structure::SingletonStructsToStruct = Func(
    Array( NVPs ),      // Array of StringValueStructures
)
Returns( StringValueStructure(), Error() )
```

---

### Structure::StructToSingletonStructs

**Splits a structure into an array of single-entry structures.**

```
Structure::StructToSingletonStructs = Func(
    ComponentValueStructure( Given Data ),
)
Returns( Array() )
```

```slang
S = {| "a" := 1, "b" := 2 |};
Result = @Structure::StructToSingletonStructs( S );
// Result: [ {| "a" := 1 |}, {| "b" := 2 |} ]
```

---

### Structure::CastToStructure

**Cast any subscriptable data to a Structure or GStructure. Optionally recurse.**

```
Structure::CastToStructure = Func(
    Any( Given Data ),
    Double( Deep )              := False,       // Recursively cast nested subscriptables
    Double( Use GStructure )    := False,       // Output GStructure instead of Structure
    Any( Prev DataType Key )    := Null,        // If set, include original type info under this key
    Array( Dont Convert Types ) := [],          // Type names to leave unconverted
)
Returns( Structure(), GStructure() )
```

```slang
Nested = {| "A" := [ GStructure( 1, "B" ) ] |};
Result = @Structure::CastToStructure( Nested, Deep := True );
// Result: {| "A" := {| "0" := {| "1" := "B" |} |} |}
```

---

## Diff / Comparison

---

### Structure::Diff

**Partial diff: returns components of X that don't exist in Y or differ from Y.**

```
Structure::Diff = Func(
    X,
    Y,
    Double( Tag Only )                  = False,    // pos arg: only compare keys, ignore values
    Double( Epsilon )                   = 0,        // pos arg: tolerance for Double comparison
    Double( Recurse )                   := False,
    Double( Cleanup )                   := False,   // Remove empty sub-structures (implies Recurse)
    Double( Array As Structure )        := False,   // Compare arrays structurally
    Double( Use SecurityIsEqual )       := False,
    ComponentValueStructure( Keys To Ignore ) := Structure(),
    Double( Case Sensitive )            := False,   // Case-sensitive string comparison
    Double( Recurse GStructures )       := False,
    Double( Recurse Typed Structures )  := True,
)
Returns( Structure(), StructureCase(), GStructure() )
```

```slang
X = {| "A" := 1, "B" := 2, "C" := 3 |};
Y = {| "A" := 1, "B" := 99 |};
D = @Structure::Diff( X, Y );
// D == {| "B" := 2, "C" := 3 |}   (B differs, C missing from Y)
```

---

### Structure::AllDiffs

**Full symmetric diff: returns all keys that differ between X and Y, recursing into sub-structures.**

```
Structure::AllDiffs = Func(
    X,
    Y,
    Double( Tag Only )  = 0,                        // pos arg
    Double( Epsilon )   = 0.0001,                   // pos arg
    Array( TagsToIgnore )               := [],
    Double( Ignore Tags Recursively )   := False,
    Double( Relative Precision )        := False,
    Double( Recurse On StructureCase )  := Null::Double,
)
Returns( Structure(), StructureCase() )
```

```slang
X = {| "A" := 1, "B" := 2, "C" := 3 |};
Y = {| "A" := 2, "B" := 3, "C" := 3 |};
D = @Structure::AllDiffs( X, Y, TagsToIgnore := [ "A" ] );
// D == {| "B" := 2 |}
```

---

### Structure::Diff Symmetric

**Symmetric diff showing both sides. Returns structures with S1/S2 sub-keys at each difference point.**

```
Structure::Diff Symmetric = Func(
    S1,
    S2,
    S1 Name := "S1",                        // Label for first structure's values
    S2 Name := "S2",                        // Label for second structure's values
    Double( Epsilon ) := 0,
    Array( Keys To Ignore ) := [],
    Double( Ignore Recursively ) := False,
    Double( Ignore Trailing Spaces On Compare ) := False,
    Double( Ignore Equivalent Securities ) := False,
    Double( Include Curves ) := False,
    Array( Matcher By Path ) := Array(),    // Custom matchers per path
    Double( Case Sensitive String Comparison ) := False,
)
Returns( ComponentValueStructure() )
```

```slang
S1 = {| "A" := {| "B" := 2 |}, "C" := 3 |};
S2 = {| "A" := {| "B" := 3 |}, "D" := 4 |};
Diffs = @Structure::Diff Symmetric( S1, S2 );
// Diffs == {|
//   "A" := {| "B" := {| "S1" := 2, "S2" := 3 |} |},
//   "C" := {| "S1" := 3 |},
//   "D" := {| "S2" := 4 |}
// |}
```

---

### Structure::Compare to Depth

**Compare two structures, but only to a given depth. Returns True if same to that depth.**

```
Structure::Compare to Depth = Func(
    ComponentValueStructure( S1 ),
    ComponentValueStructure( S2 ),
    Double( Depth ),            // 0 = always True; 1 = compare keys only; etc.
)
Returns( Double() )
```

```slang
X1 = {| "a" := {| "a1" := 1 |}, "b" := {| "b1" := 2 |} |};
X2 = {| "a" := {| "a1" := 1 |}, "b" := {| "b1" := 99 |} |};
@Structure::Compare to Depth( X1, X2, 1 );  // True  (same keys at depth 1)
@Structure::Compare to Depth( X1, X2, 3 );  // False (values differ at depth 3)
```

---

### Structure::Det Diff In Arrays Of Structs

**Compare two arrays of structures, matching by specified tags. Returns Modified / New / Removed.**

```
Structure::Det Diff In Arrays Of Structs = Func(
    Array( Array1 ),
    Array( Array2 ),
    Array( Ignorable Tags ),        // Tags to ignore in diffs
    Array( Matching Tags ),         // Tags used to match entries
    Double( Ignore Tags Recursively ) := False,
)
Returns( Structure() )    // Keys: "Modified", "New", "Removed"
```

---

## Deep Entry / Path Access

---

### Structure::Add Deep Entry

**Adds a value at a nested path, creating intermediate structures as needed.**

```
Structure::Add Deep Entry = Func(
    ComponentValueStructure( &Struct ),  // Modified in place (pass by reference)
    Array( Path ),                       // Array of strings specifying the path
    Any( Value ) = Structure(),          // Value to insert
    String( Op ) := "Replace",          // Operation: "Replace", "Add", "Append", "Concat",
                                        //   "Set If Missing", "Unique", "SetUnique", "SetNull", ""
)
Returns()
```

Operations:
- **"Replace"** -- overwrite existing value (default)
- **"Add"** -- arithmetic add (`+=`) to existing value
- **"Append"** -- append to array (`&=`)
- **"Concat"** -- `ArrayConcatInPlace` for arrays
- **"Set If Missing"** -- only set if path has no value
- **"Unique"** -- throws if path already has a value
- **"SetUnique"** -- throws if path has a *different* value
- **"SetNull"** -- sets value to Null
- **""** -- creates empty sub-structures along path, no value set

```slang
S = {| |};
@Structure::Add Deep Entry( &S, [ "Level1", "Level2" ], 42 );
// S == {| "Level1" := {| "Level2" := 42 |} |}

@Structure::Add Deep Entry( &S, [ "Level1", "Values" ], 1, Op := "Append" );
@Structure::Add Deep Entry( &S, [ "Level1", "Values" ], 2, Op := "Append" );
// S.Level1.Values == [ 1, 2 ]
```

---

### Structure::Entry

**One-stop shop for nested structure entry get/set. Returns a pointer.**

```
Structure::Entry = Func(
    &A,                             // Nested structure/array (pass by reference)
    Array( Path ),                  // Path like [ 1, "b", 1 ]
    InitMissingTo = Null,           // Null: don't create; Structure()/[]: use defaults;
                                    //   String: datatype name; Array: per-level types;
                                    //   Structure: type mapping
)
Returns( Pointer(), Null )
```

Use `*Ptr = value` to set values, or `*Ptr` to read. Returns `Null` (as error) if path doesn't exist and `InitMissingTo` is Null.

Special: `-1` as array subscript means "append".

```slang
// Change an existing entry
A = [ 0, {| "b" := [ 0, 2 ] |} ];
*@Structure::Entry( &A, [ 1, "b", 1 ] ) = 3;
// A[1].b[1] is now 3

// Test for existence
A = {| "X" := {| "Y" := 1 |} |};
Exists = !IsError( @Structure::Entry( &A, [ "X", "Y" ] ) );      // True
Missing = !IsError( @Structure::Entry( &A, [ "X", "Z" ] ) );      // False

// Create new entries with append
A = {| |};
*@Structure::Entry( &A, [ "X", -1 ], [] ) = 5;
*@Structure::Entry( &A, [ "X", -1 ], [] ) = 4;
// A == {| "X" := [ 5, 4 ] |}
```

---

### Structure::IsLeaf

**Returns True if the argument is not a nested type (not Structure, Array, etc.).**

```
Structure::IsLeaf = Func(
    Any( Obj ),
)
Returns( Double() )
```

---

## Iteration / Map / Fold

---

### Structure::ForEachKeyVal

**Applies a function of (key, value) to each entry, returning an array of results.**

```
Structure::ForEachKeyVal = Func(
    ComponentValueStructure( S ),
    Slang( F ),                 // Func( key, value ) -> result
)
Returns( Array() )
```

```slang
S = {| "A" := 1, "B" := 2 |};
Result = @Structure::ForEachKeyVal( S, \k, v -> Sprint( k, "=", v ) );
// Result: [ "a=1", "b=2" ]
```

---

### Structure::KeyVal Mapcar

**Like `Mapcar` but on structures, with access to both key and value. Preserves structure shape/type.**

```
Structure::KeyVal Mapcar = Func(
    Slang( F ),                     // Func( key, value ) -> new value
    SubscriptableDatatype( S ),
)
Returns( SubscriptableDatatype() )
```

```slang
Result = @Structure::KeyVal Mapcar( \k, v -> k + String( v ), {| "foo" := 1, "bar" := 2 |} );
// Result: {| "foo" := "foo1", "bar" := "bar2" |}
```

---

### Structure::KeyVal Foldl

**Like `Foldl` but on structures, with access to both key and value.**

```
Structure::KeyVal Foldl = Func(
    Slang( F ),                         // Func( key, value, accumulator ) -> new accumulator
    Any( Init ),                        // Initial accumulator
    SubscriptableDatatype( S ),
    Double( Commutative ) := True,      // If False, iterates in sorted key order (slower)
)
Returns( Any() )
```

```slang
Result = @Structure::KeyVal Foldl(
    \k, v, acc -> Sprint( acc, k, v, "," ),
    "",
    {| "foo" := 1, "bar" := 2 |},
    Commutative := False
);
// Result: "bar2,foo1,"
```

---

### Structure::KeyApply

**Apply a function to all keys, producing a GStructure.**

```
Structure::KeyApply = Func(
    Any( Struc ),           // Structure, GStructure, or StructureCase
    Slang( KeyFunc ),       // Func( key ) -> new key
)
Returns( GStructure() )
```

---

### Structure::ValApply

**Apply a function to all values. Deprecated: use `Mapcar` instead.**

```
Structure::ValApply = Func(
    ComponentValueStructure( Struc ),
    Slang( ValFunc ),           // Func( value ) -> new value
)
Returns( ComponentValueStructure() )
```

---

### Structure::Map

**Build a structure from an array of keys by applying a function to each key.**

```
Structure::Map = Func(
    Array( Keys ),
    Slang( f ),                 // Func( key ) -> value
    Double( Case ) := False,   // Return StructureCase
    Double( G ) := False,      // Return GStructure
)
Returns( ComponentValueStructure() )
```

```slang
Result = @Structure::Map( [ "a", "b", "c" ], \x -> Asc( x ) );
// Result: {| "a" := 97, "b" := 98, "c" := 99 |}
```

---

### Structure::SMap

**Like `Map`, but takes an existing structure and re-maps its values by applying `f` to each key.**

```
Structure::SMap = Func(
    ComponentValueStructure( S ),
    Slang( f ),                     // Func( key ) -> new value
)
Returns( ComponentValueStructure() )
```

---

## Fold / Unfold Array Leaves

---

### Structure::Fold In Array Leaves

**Converts array leaf values into nested structures using a key array. Useful for dimensioning data.**

```
Structure::Fold In Array Leaves = Func(
    Structure( &X ),
    Array( Key Array ),
    Double( Allow Less Values ) := False,
    Double( Fold Into Empty Parent Keys ) := True,
)
Returns( Double() )    // Number of times folding occurred
```

---

### Structure::Unfold Array Leaves

**Reverses `Fold In Array Leaves` -- converts structure leaves back to arrays.**

```
Structure::Unfold Array Leaves = Func(
    Structure( &X ),
    Array( Key Array ),
    Double( Allow Less Values ) := False,
    Array( Sorted Key Array ) := [],
)
Returns()
```

---

## Pruning / Reset

---

### Structure::PruneZero

**Recursively removes zero-valued doubles and optionally empty sub-structures.**

```
Structure::PruneZero = Func(
    ComponentValueStructure( &s ),              // Modified in place
    Delete Empty Structures = False,            // pos arg: remove empty sub-structures
    Double( Threshold )     = 0,                // pos arg: remove values <= threshold
    Double( Destroy Error ) := False,           // Also remove Error values
    Double( Prune Curves )  := False,           // Also prune zero curves
    Array( KeysToSkip )     := [],              // Keys to skip entirely
)
Returns()
```

```slang
S = {| "A" := 0, "B" := 5, "C" := {| "D" := 0, "E" := 3 |} |};
@Structure::PruneZero( &S );
// S == {| "B" := 5, "C" := {| "E" := 3 |} |}

// With threshold
S2 = {| "X" := 0.00001, "Y" := 1 |};
@Structure::PruneZero( &S2, False, 0.001 );
// S2 == {| "Y" := 1 |}
```

---

### Structure::ResetValues

**Recursively sets all Doubles to 0 and all Strings to "" (or custom values).**

```
Structure::ResetValues = Func(
    Any( &s ),
    Any( Doubles ) := 0,       // Value for Double elements
    Any( Strings ) := "",      // Value for String elements
)
Returns( Double() )    // True if structure is non-empty
```

---

## Display / Printing

---

### Structure::Print Simple

**Prints a structure as a single-line string to stdout.**

```
Structure::Print Simple = Func(
    Structure( Struct ),
)
Returns()
```

---

### Structure::As Single Line String

**Returns a single-line string representation of a structure.**

```
Structure::As Single Line String = Func(
    StringValueStructure( Struct ),
    Double( Double Rounding ) := -1,        // -1 for no rounding
    Double( Double Flags )    := _Commas,   // format flags for doubles
    Double Width              := Null,      // max width for double fields
    String( Tuple Delimiter ) := ", ",      // delimiter between key=value pairs
    Double( Recursive )       := False,     // recurse into nested structures
    Double( Shorthand )       := False,     // use {| key:=value |} notation
    String( Key Value Delimiter ) := If( Shorthand ) ":=" : "=",
    Double( Remove Spaces )   := False,     // remove all whitespace (not invertible)
)
Returns( String() )
```

```slang
S = {| "a" := 100, "b" := "Hello" |};
Str = @Structure::As Single Line String( S );
// "a=100, b=Hello"

Str2 = @Structure::As Single Line String( S, Shorthand := True, Recursive := True );
// "{| a:=100, b:=Hello |}"
```

---

## Querying

---

### Structure::ArrayOfTags

**Returns the sorted keys of a structure as an array. Arrays pass through unchanged.**

```
Structure::ArrayOfTags = Func(
    Any( Struct ),
)
Returns( Array() )
```

---

### Structure::All Keys

**Recursively collects all keys from a nested structure (unsorted, with duplicates).**

```
Structure::All Keys = Func(
    ComponentValueStructure( X ),
    Double( Structure Only ) := True,   // Only recurse into Structures (not StructureCase etc.)
)
Returns( Array() )
```

```slang
S = {| "A" := {| "B" := 1, "C" := {| "D" := 2 |} |}, "E" := 3 |};
Keys = @Structure::All Keys( S );
// Keys contains: [ "A", "E", "B", "C", "D" ]
```

---
---

# Functions from `_LIB Structure Functions 2`

The functions below live in `_LIB Structure Functions 2`, which is internally linked
by the umbrella `_LIB Structure Functions`.

---

## Validation / Depth

---

### Structure::Validate Structure

**Returns True if every component named in the `Components` array exists in `Data`.**

```
Structure::Validate Structure = Func(
    Any( Data ),
    Any( Components ),          // Array of component names
)
Returns( Double() )
```

---

### Structure::Validate Depth

**Returns True if every branch of a (non-empty) structure reaches exactly `Depth` levels.**

```
Structure::Validate Depth = Func(
    ComponentValueStructure( X ),
    Double( Depth ),
)
Returns( Double() )
```

---

### Structure::Ensure Min Depth

**Pads a structure in-place so every branch is at least `Depth` levels deep.**

```
Structure::Ensure Min Depth = Func(
    &X,
    Double( Depth ),
    Any( Default Key )      = "",
    Any( Default Value )    = 0.0,
)
Returns()
```

---

### Structure::Enforce Depth

**Ensures a structure has *exactly* the given depth by padding shallow branches
and collapsing deep ones via `StructureRedimension`.**

```
Structure::Enforce Depth = Func(
    ComponentValueStructure( &X ),
    Double( Depth ),
    Any( Insert Key )   = "",
    Any( Insert Value ) = 0.0,
)
Returns()
```

---

### Structure::Relax Depth

**Reverses the padding introduced by `Enforce Depth`. Removes levels whose sole
key equals `Insert Key`.**

```
Structure::Relax Depth = Func(
    ComponentValueStructure( &X ),
    Any( Insert Key )   = "",
    Any( Insert Value ) = 0.0,
)
Returns()
```

---

## Path Access (Get / Set / Destroy)

---

### Structure::Set By Path

**Sets a deep value: `@Structure::Set By Path( &S, [ "A", "B" ], 42 )` makes `S.A.B == 42`.
Creates intermediate structures automatically.**

```
Structure::Set By Path = Func(
    &s,
    Array( Path ),
    d,
    Double( Merge )                         := False,
    Double( Preserve DataType on Merge )    := False,
    Any( Leaf Node )                        := Null,
)
Returns()
```

---

### Structure::Get By Path

**Retrieves a deep value: `@Structure::Get By Path( &S, [ "A", "B" ] )` returns `S.A.B`.
Optional `Default` returned when a key is missing (otherwise redboxes).**

```
Structure::Get By Path = Func(
    Any( &S ),
    Array( Path ),
    Double( i ) = 0,
    Any( Default )                                  := <sentinel>,
    Double( Return Null on Missing Component )      := False,
)
Returns( Any() )
```

---

### Structure::Get By Path Deep

**Like `Get By Path`, but if the path does not start at the top level it searches
deeper in the tree until it finds a match.**

```
Structure::Get By Path Deep = Func(
    Any( &S ),
    Array( Path ),
    Any( Default ) := <sentinel>,
)
Returns( Any() )
```

```slang
S = {| A := {| B := {| C := {| D := 1 |} |} |} |};
@Structure::Get By Path Deep( &S, [ "C", "D" ] );  // 1  (found via A.B.C.D)
```

---

### Structure::Get By Uri Path

**Like `Get By Path`, but supports wildcard segments of the form `:name` that
match any key and optionally capture the matched value into a `Path Params` structure.**

```
Structure::Get By Uri Path = Func(
    Any( S ),
    Array( Path ),
    Any( Default )                  := Null,
    Structure( &Path Params )       := <no capture>,
)
Returns( Any() )
```

---

### Structure::Destroy By Path

**Removes a deep entry: `@Structure::Destroy By Path( &S, [ "A", "B" ] )` destroys `S.A.B`.
`Clean Up Empty Paths` prunes empty parent structures. `Clean Array Elements` shifts array indices.**

```
Structure::Destroy By Path = Func(
    &s,
    Array( Path ),
    Double( Clean Up Empty Paths )  := False,
    Double( Clean Array Elements )  := False,
)
Returns()
```

---

## Sorting

---

### Structure::Sorted by Values

**Returns `[ [ k1, v1 ], [ k2, v2 ], ... ]` sorted by value using the optional comparator.**

```
Structure::Sorted by Values = Func(
    S,
    Slang( Comparator ) = Func( a, b ) a <=> b,
)
Returns( Array() )
```

```slang
abc = {| A := 0, B := 13, C := 2 |};
@Structure::Sorted by Values( abc );
// [ [ "A", 0 ], [ "C", 2 ], [ "B", 13 ] ]
```

---

### Structure::Sorted by Keys

**Returns `[ [ k1, v1 ], [ k2, v2 ], ... ]` sorted by key using the optional comparator.**

```
Structure::Sorted by Keys = Func(
    ComponentValueStructure( S ),
    Slang( Comparator ) = Func( a, b ) a <=> b,
)
Returns( Array() )
```

---

### Structure::Sorted by Values Deep

**Flattens a nested structure into `[ [ path, value ], ... ]` sorted by leaf value.**

```
Structure::Sorted by Values Deep = Func(
    ComponentValueStructure( S ),
    Slang( Comparator ) = Func( a, b ) a <=> b,
)
Returns( Array() )
```

```slang
S = {| a := {| b := 1, c := -2 |}, d := 0.5 |};
@Structure::Sorted by Values Deep( S );
// [ [ [ "a", "c" ], -2 ], [ [ "d" ], 0.5 ], [ [ "a", "b" ], 1 ] ]
```

---

## Renaming

---

### Structure::Rename Components

**Renames keys in every structure in an array according to a map. Wraps `Rename Components Single`.**

```
Structure::Rename Components = Func(
    Array( Values ),
    ComponentValueStructure( Map ),
)
Returns( Array() )
```

---

### Structure::Rename Components Single

**Renames keys in a single structure according to a map. Keys absent from the map keep their original name.**

```
Structure::Rename Components Single = Func(
    ComponentValueStructure( In Struct ),
    ComponentValueStructure( Map ),
)
Returns( ComponentValueStructure() )
```

---

### Structure::Rename Components By Path

**Renames deep paths in a structure. Each entry in the GStructure map is `[ from_path ] -> [ to_path ]`.**

```
Structure::Rename Components By Path = Func(
    ComponentValueStructure( &S ),
    GStructure( Map ),
    Double( Clean Up Empty Paths ) := False,
)
Returns()
```

---

### Structure::KeyRename InPlace

**Recursively renames keys in a structure in-place according to a Rename Map. Optionally processes children first (`Down First`).**

```
Structure::KeyRename InPlace = Func(
    StringValueStructure( &S ),
    Structure( Rename Map ),
    Double( Down First ) := False,
)
Returns()
```

---

## Leaf / Key Traversal

---

### Structure::Apply to Leaves

**Applies a function to every non-structure leaf of a nested structure, modifying in place.**

```
Structure::Apply to Leaves = Func(
    &S,
    Slang( F ),
    Double( Recurse Arrays ) := False,
    String( Recurse Kind )   := "ComponentValueStructure",
)
Returns()
```

```slang
S = {| A := 1, B := {| C := 2, D := 3 |} |};
@Structure::Apply to Leaves( &S, Func( x ) Pow( 2, x ) );
// S is now {| A := 2, B := {| C := 4, D := 8 |} |}
```

---

### Structure::Transform Leaves

**Same as `Apply to Leaves` but returns the result instead of modifying in place.**

```
Structure::Transform Leaves = Func(
    ComponentValueStructure( S ),
    Slang( F ),
    Double( Recurse Arrays ) := False,
)
Returns( ComponentValueStructure() )
```

---

### Structure::Apply to Keys

**Applies a function to every key in a nested structure. Optional `Depth` limits how many levels deep. `Agg Func` merges values when two keys collide after renaming.**

```
Structure::Apply to Keys = Func(
    ComponentValueStructure( S ),
    Slang( F ),
    Double( Depth )             := Error Value,     // all levels
    Slang( Agg Func )           := Slang(),
    Double( Recurse Arrays )    := False,
)
Returns( ComponentValueStructure() )
```

```slang
S = {| A := 1, B := {| C := 2, D := 3 |} |};
@Structure::Apply to Keys( S, Func( x ) x + "Z" );
// {| AZ := 1, BZ := {| CZ := 2, DZ := 3 |} |}
```

---

### Structure::Get Leaves

**Returns an array of all non-structure values (leaves) from a nested structure.**

```
Structure::Get Leaves = Func(
    ComponentValueStructure( Input ),
)
Returns( Array() )
```

```slang
@Structure::Get Leaves( {| A := "X", B := {| C := "Y" |} |} );
// [ "X", "Y" ]
```

---

### Structure::Get Leaf Keys

**Returns an array of the keys at the lowest (leaf) level of a nested structure.**

```
Structure::Get Leaf Keys = Func(
    ComponentValueStructure( Input ),
)
Returns( Array() )
```

---

### Structure::Get Leaf Keys and Values

**Returns `{| Keys := [...], Leaves := [...] |}` with both the leaf keys and leaf values.**

```
Structure::Get Leaf Keys and Values = Func(
    ComponentValueStructure( Input ),
)
Returns( Structure() )
```

---

## Union / Intersect (Extended)

---

### Structure::Union

**Non-destructive StructureUnion: `@Structure::Union( A, B, C, ... )`. Precedence goes to the *first* argument for shared keys.**

```
Structure::Union = Func(
    ComponentValueStructure( A ),
    Ellipsis( B ) = [],
)
Returns( ComponentValueStructure() )
```

> **Tip:** Put overrides *first*: `@Structure::Union( overrides, base )`.

---

### Structure::Struct Union

**Like `Union` but with a default empty structure for A.**

```
Structure::Struct Union = Func(
    ComponentValueStructure( A ) = {||},
    Ellipsis( B ) = [],
)
Returns( ComponentValueStructure() )
```

---

### Structure::Union upto Level

**Stops the recursive StructureUnion at the given level.**

```
Structure::Union upto Level = Func(
    Array( A ),
    Double( Level ),
)
Returns( ComponentValueStructure() )
```

---

### Structure::Union Deep

**Recursive deep union. Collision resolver determines how leaf values merge (default: array concatenation).**

```
Structure::Union Deep = Func(
    ComponentValueStructure( LStructure ),
    ComponentValueStructure( RStructure ),
    Slang( Collision Resolver ) := \x,y -> { ... },
)
Returns( ComponentValueStructure() )
```

---

### Structure::StrictUnion

**Union that throws if A and B share a key with differing values.**

```
Structure::StrictUnion = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
)
Returns( ComponentValueStructure() )
```

---

### Structure::Intersect

**Recursive intersection of two structures. Values come from A unless listed in `B Tags`.**

```
Structure::Intersect = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
    ComponentValueStructure( B Tags ) := {||},
    Double( Allow GStructure )        := False,
)
Returns( ComponentValueStructure() )
```

---

### Structure::Copy Common Values

**Copies values from `From` to `To` for common keys, recursively. `Skip Tags` prevents specific keys from being overwritten.**

```
Structure::Copy Common Values = Func(
    StringValueStructure( To ),
    StringValueStructure( From ),
    StringValueStructure( Skip Tags ) := {||},
)
Returns( StringValueStructure() )
```

---

### Structure::Intersection with Values

**Like `Intersection`, but also compares *values* (not just keys). Returns only entries where both key and value match.**

```
Structure::Intersection with Values = Func(
    Any( StructX ),
    Any( StructY ),
    Double( Array As Structure )             := False,
    Double( Typed Structure as Structure )    := True,
)
Returns( Any() )
```

---

### Structure::Keys Intersection

**Returns an array of keys common to A and B at the top level only (fast, non-recursive).**

```
Structure::Keys Intersection = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
)
Returns( Array() )
```

---

### Structure::Common Values

**Identifies key-value pairs common to *all* structures in an array. `Deep` does so recursively.**

```
Structure::Common Values = Func(
    Array( Structures ),
    Double( Deep ) := False,
)
Returns( ComponentValueStructure() )
```

---

## Grouping / Categorizing

---

### Structure::Group By

**Groups values by applying a `Group By` function to keys. Values sharing the same group key are merged (default: array append).**

```
Structure::Group By = Func(
    ComponentValueStructure( Input ),
    Slang( Group By ),
    Slang( Merge )      := Func( X, Y ) { X &= Y; X },
    Any( Initial Value ) := [],
    ComponentValueStructure( Out ) := New( TypeOf( Input ) ),
)
Returns( ComponentValueStructure() )
```

```slang
@Structure::Group By(
    {| A1 := 3, A2 := 5, B1 := 4 |},
    Func( K ) SubStr( K, 0, 0 ),
);
// {| A := [ 3, 5 ], B := [ 4 ] |}
```

---

### Structure::Categorize

**Categorizes each value by applying a two-arg `Categorizer( key, value )` that returns a category key. Result: GStructure of arrays.**

```
Structure::Categorize = Func(
    Any( Array or Structure ),
    Slang( Categorizer ),
    ComponentValueStructure( Out ) = GStructure(),
    Double( Multiple Categories )  := False,
)
Returns( ComponentValueStructure() )
```

```slang
@Structure::Categorize( [ "One", "Two", "Four" ], \_,Y -> Size( Y ) );
// GStructure( 3, [ "One", "Two" ], 4, [ "Four" ] )
```

---

### Structure::Categorize As Tree

**Like `Categorize` but preserves key-value mappings under each category instead of flattening to arrays.**

```
Structure::Categorize As Tree = Func(
    Any( Struct ),
    Slang( Categorizer ),
    Double( Multiple Categories ) := False,
)
Returns( GStructure() )
```

---

### Structure::Aggregate Structure

**Aggregates a structure by grouping keys with a `Group By` function, then merging values with a `Merge` function (default: addition).**

```
Structure::Aggregate Structure = Func(
    Structure( &Risk ),
    Slang( Group By ),
    Slang( Merge ) = \X,Y -> X + Y,
    String( Null Key ) := "",
)
Returns( Structure() )
```

---

## Aggregation

---

### Structure::Aggregate

**Applies a built-in aggregation function (e.g. `"Max"`, `"Sum"`) or a custom Slang function across an array of structures, key by key. Recurses into nested sub-structures.**

```
Structure::Aggregate = Func(
    Array( Structures ),
    String( Aggregation ) = "",
    Slang( Slang Agg )    := Slang(),
)
Returns( Structure(), StructureCase(), GStructure(), Error() )
```

---

### Structure::Max / Structure::Min / Structure::Sum

**Convenience wrappers around `Aggregate`.**

```
Structure::Max = Func( Array( Structures ) ) ...
Structure::Min = Func( Array( Structures ) ) ...
Structure::Sum = Func( Array( Structures ) ) ...
```

---

## Diff (Reporting)

---

### Structure::DiffReport

**Generates a human-readable structure showing differences between A and B.
Uses `< ` / `> ` prefixes and supports a numeric tolerance.**

```
Structure::DiffReport = Func(
    A,
    B,
    Double( Tolerance )     := 1e-10,
    Double( Case Sensitive ) := False,
)
Returns( Structure() )
```

---

### Structure::Minus

**Removes entries from A that are equal to B, recursively.
Modifies A in-place. If A == B, A is destroyed.**

```
Structure::Minus = Func(
    &A,
    &B,
    Double( Tolerance )        := 0.0,
    Double( IgnoreReferences ) := False,
)
Returns()
```

---

### Structure::Cmp Structures

**Recursively compares two structures and prints human-readable differences to stdout. Returns a count of differences.**

```
Structure::Cmp Structures = Func(
    Structure( Lhs ),
    Structure( Rhs ),
    Idx = [],
    Double( Tol )       := 1e-4,
    String( Diff Fmt )  := "%15.4f",
    Double( Detailed )  := True,
    Array( Tags )       := [ "Lhs", "Rhs" ],
)
Returns( Double() )
```

---

### Structure::Diff Symmetric Flatten

**A symmetrical diff which produces a flattened result set with `Label 1` and `Label 2` columns.**

```
Structure::Diff Symmetric Flatten = Func(
    Structure( Struc 1 ),
    Structure( Struc 2 ),
    Array( Keys To Ignore )  := [],
    Double( Recurse )        := False,
    Double( Full Recurse )   := False,
    String( Label 1 )        := "Structure 1",
    String( Label 2 )        := "Structure 2",
    Double( Epsilon )        := 0,
    ...
)
Returns( Structure() )
```

---

## Cross Product / Cartesian

---

### Structure::Cross Array of Struct

**Cross product of two arrays of structures. Each element of A is unioned with each element of B.**

```
Structure::Cross Array of Struct = Func(
    Array( A ),
    Array( B ),
)
Returns( Array() )
```

---

### Structure::Cross Struct of Array

**Given a struct of N arrays, enumerates every N-ary combination (Cartesian product). Returns an array of structures.**

```
Structure::Cross Struct of Array = Func(
    Structure( S ),
    Double( Sorted Order ) := False,
)
Returns( Array() )
```

```slang
@Structure::Cross Struct of Array(
    {| x := [ 1, 2 ], y := [ "a", "b" ] |}
);
// [ {| x := 1, y := "a" |}, {| x := 1, y := "b" |},
//   {| x := 2, y := "a" |}, {| x := 2, y := "b" |} ]
```

---

### Structure::Cartesian Product

**Like `Cross Struct of Array` but more flexible: supports `Result Constructor` (for typed structures) and `Exclude Combination` filter.**

```
Structure::Cartesian Product = Func(
    ComponentValueStructure( Values ),
    Slang( Result Constructor )  := ...,
    Slang( Exclude Combination ) := \_ -> False,
)
Returns( Array() )
```

---

### Structure::Cross Product

**Returns the cross (outer) product of two structures, multiplying leaf values.**

```
Structure::Cross Product = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
    Slang( Product ) := \x,y -> x*y,
)
Returns( ComponentValueStructure() )
```

---

## Conversion (Extended)

---

### Structure::StructOfStructToArrayOfStruct

**Converts `{| a := {| ... |}, b := {| ... |} |}` to `[ {| Label := "a", ... |}, {| Label := "b", ... |} ]`. The top-level key becomes a component `Tag` in each result.**

```
Structure::StructOfStructToArrayOfStruct = Func(
    GrowableStringValueStructure( Struct ),
    String( Tag ),
)
Returns( Array() )
```

---

### Structure::StructOfStructToArrayOfArray

**Recursively flattens a nested structure into an array of arrays (paths + leaf values).**

```
Structure::StructOfStructToArrayOfArray = Func(
    Structure( Struct ),
)
Returns( Array() )
```

---

### Structure::From Array Of Array

**Inverse of `To Array of Array`. Builds a nested structure from a 2D array of `[ key, key, ..., value ]` rows.**

```
Structure::From Array Of Array = Func(
    Array( A ),
    Double( Sum Elements ) = False,
)
Returns( Structure() )
```

---

### Structure::StructOfArrayToArrayOfStructMany

**Converts a struct of arrays to all unique combinations (Cartesian), returning an array of structures.**

```
Structure::StructOfArrayToArrayOfStructMany = Func(
    ComponentValueStructure( X ),
)
Returns( Array() )
```

---

### Structure::From GStructure

**Converts a GStructure to a Structure (or StructureCase) by converting keys to strings.**

```
Structure::From GStructure = Func(
    GStructure( GStruct ),
    Double( StructureCase )           := False,
    Double( Check for Collisions )    := True,
    Double( Recursive )               := False,
)
Returns( Structure(), StructureCase() )
```

---

### Structure::ArrayOfStructToStructNested

**Converts an array of flat structures (a table) into a nested tree keyed by the specified nesting columns.**

```
Structure::ArrayOfStructToStructNested = Func(
    Array( Input Array ),
    Array( Nesting Keys ),
    Double( Multiple Tags )     := False,
    Double( RemoveTag )         := True,
    Double( TagCaseSensitive )  := False,
)
Returns( Structure(), StructureCase(), GStructure() )
```

---

### Structure::TableInit

**Like built-in `TableInit()` but returns an array of StructureCases (or the type you specify).**

```
Structure::TableInit = Func(
    Array( The Table ),
    ComponentValueStructure( Type ) := StructureCase(),
)
Returns( Array() )
```

---

### Structure::FromKeysWithDuplicates

**Like `StructureFromKeys` but handles duplicate keys efficiently.**

```
Structure::FromKeysWithDuplicates = Func(
    Array( Keys ),
    Array( Values ),
    Double( Initial Size )   = 0,
    Double( Case Sensitive ) := False,
)
Returns( {||} )
```

---

## Filtering (Extended)

---

### Structure::Filter Dimensions

**Filters a multi-level structure by specifying allowed values at each dimension level. Supports strings, structures (multi-value), RegEx, and Slang functions as filters.**

```
Structure::Filter Dimensions = Func(
    Structure( X ),
    Array( Filter Map ),
    Double( Remove Empty Branches ) := True,
)
Returns( Structure() )
```

---

### Structure::Filter Out Dimensions

**The inverse of `Filter Dimensions`: keeps everything *except* what the filter matches.**

```
Structure::Filter Out Dimensions = Func(
    Structure( X ),
    Array( Filter Map ),
    Double( Remove Empty Branches ) := True,
)
Returns( Structure() )
```

---

### Structure::Filter At Level

**Filters a nested structure at a specified depth level.**

```
Structure::Filter At Level = Func(
    ComponentValueStructure( S ),
    Double( Level ),
    Slang( Filter ),
    Double( Filter by Keys )                := False,
    Double( Keep Empty Values )             := False,
    Double( Throw on Insufficient Depth )   := True,
)
Returns( ComponentValueStructure() )
```

---

### Structure::Match Keys

**Returns components whose key contains the given substring.**

```
Structure::Match Keys = Func(
    Structure( S ),
    String( Subkey ),
)
Returns( Structure() )
```

---

### Structure::Grep

**Removes all key-value pairs for which the filter function returns False.**

```
Structure::Grep = Func(
    Any( Struct ),
    Slang( Filter ),
)
Returns( Any() )
```

---

### Structure::Extract Value

**Returns a structure of only those key-value pairs whose values equal `To Extract` (or satisfy the optional `Matcher` function).**

```
Structure::Extract Value = Func(
    ComponentValueStructure( In ),
    Any( To Extract ),
    Slang( Matcher ) := Slang(),
)
Returns( Structure(), GStructure(), StructureCase() )
```

---

### Structure::Extract Values as Array

**Given keys `[ k1, k2, ... ]`, returns `[ S[ k1 ], S[ k2 ], ... ]`.
Returns `Default Value` for missing keys.**

```
Structure::Extract Values as Array = Func(
    ComponentValueStructure( Struct ),
    Array( Keys ),
    Any( Default Value ) = Null,
)
Returns( Array() )
```

---

## Path Querying

---

### Structure::Get All Paths

**Returns all valid paths (as arrays of keys) in a nested structure.**

```
Structure::Get All Paths = Func(
    Any( &Str ),
    Double( Depth ) = 0,
    String( Struct Type ) := "ComponentValueStructure",
)
Returns( Array() )
```

```slang
x = {| "3" := {| "1" := 1, "2" := 2 |} |};
@Structure::Get All Paths( &x );
// [ [ "3", "1" ], [ "3", "2" ] ]
```

---

### Structure::Get All Paths To Value

**Returns all paths that lead to a specific value.**

```
Structure::Get All Paths To Value = Func(
    Any( &Str ),
    Any( Value ),
    Double( Depth ) = 0,
    String( Struct Type ) := "ComponentValueStructure",
)
Returns( Array() )
```

---

### Structure::Get All Paths with Filter

**Like `Get All Paths` but only explores paths matching a level-based filter map.**

```
Structure::Get All Paths with Filter = Func(
    Any( &Str ),
    ComponentValueStructure( Filter ),
)
Returns( Array() )
```

---

### Structure::Find All Paths For Key

**Finds all paths that lead to a specific key name in a nested structure.**

```
Structure::Find All Paths For Key = Func(
    ComponentValueStructure( X ),
    String( Key ),
    Double( Truncate Paths )        := True,
    Double( Case Sensitive )        := False,
    Double( Include Empty Paths )   := False,
    Double( Decompose Array )       := False,
)
Returns( Array() )
```

---

### Structure::Find Overrides All

**Finds all paths to `Replace` in `Base`, then builds a structure with `Value` at each path.**

```
Structure::Find Overrides All = Func(
    ComponentValueStructure( Base ),
    String( Replace ),
    Any( Value ),
)
Returns( Structure() )
```

---

### Structure::Find And Replace All

**Finds all paths to `Replace` in `X` and replaces each with `Value` (in place). Returns the paths found.**

```
Structure::Find And Replace All = Func(
    ComponentValueStructure( &X ),
    String( Replace ),
    Any( Value ),
    Double( Apply Value Function ) := False,
)
Returns( Array() )
```

---

### Structure::Max Depth

**Returns the maximum depth of all branches in a nested structure.**

```
Structure::Max Depth = Func(
    Any( &Str ),
)
Returns( Double() )
```

```slang
x = {| A := {| B := True |} |};
@Structure::Max Depth( &x );   // 2
```

---

## Misc Utilities

---

### Structure::One Liner

**Returns a single-line string representation: `"a = 1 , b = 2"`.**

```
Structure::One Liner = Func(
    Any( X ),
    String( Glue )              := " , ",
    String( Key Val Separator ) := " = ",
)
Returns( String() )
```

---

### Structure::Map Of

**Creates a structure from an array of keys with all values set to True (or a custom values array).**

```
Structure::Map Of = Func(
    Array( Keys ),
    Array( Values ) := ArrayInitialize( Size( Keys ), True ),
)
Returns( Structure() )
```

---

### Structure::Is Subset Of

**Returns True if every element of `Subset List` appears in `Superset List`.**

```
Structure::Is Subset Of = Func(
    Array( Subset List ),
    Array( Superset List ),
)
Returns( Double() )
```

---

### Structure::Compose

**Composes structures as mathematical functions: `C[ x ] = B[ A[ x ] ]`.**

```
Structure::Compose = Func(
    ComponentValueStructure( A ),
    ComponentValueStructure( B ),
    Double( All A Keys ) = True,
)
Returns( ComponentValueStructure() )
```

---

### Structure::DotProduct

**Element-wise multiplication of two structures (recurses into sub-structures).**

```
Structure::DotProduct = Func(
    Structure( A ),
    Structure( B ),
)
Returns( Structure() )
```

---

### Structure::Differentiate

**Given `{| X := [...], Y := [...] |}`, returns `dY/dX` as a structure of the same form.**

```
Structure::Differentiate = Func(
    Structure( S ),
    Double( Order ) = 1,
)
Returns( Structure() )
```

---

### Structure::Bucket

**Splits a structure into N buckets (array of structures), distributing keys round-robin.**

```
Structure::Bucket = Func(
    StringValueStructure( Structure ),
    Double( Number Of Buckets ) = Size( Structure ),
    Double( Destroy Empty Buckets ) := True,
)
Returns( Array() )
```

---

### Structure::Contains

**Returns True if the entry appears anywhere as a key or leaf value (recursive).**

```
Structure::Contains = Func(
    Structure( Struct ),
    Any( Entry ),
)
Returns( Double() )
```

---

### Structure::Component Exists Deep

**Returns True if the component exists anywhere in the structure tree (recursing into arrays etc.).**

```
Structure::Component Exists Deep = Func(
    Any( X ),
    String( Component ),
)
Returns( Double() )
```

---

### Structure::Truncate Structure

**Walks the structure and replaces any sub-structure containing `TruncTag` with the value of that tag.**

```
Structure::Truncate Structure = Func(
    Structure( X ),
    String( TruncTag ),
)
Returns( Any() )
```

---

### Structure::Partially Structure Table

**Takes a table (array of structures) and indexes by specified dimensions to create a nested structure of tables.**

```
Structure::Partially Structure Table = Func(
    Array( Table ),
    Array( Dimensions ),
    Double( ToString ) = False,
    Double( Unique )   = False,
    String( Return )   := "Structure",
)
Returns( ComponentValueStructure() )
```

---

### Structure::Redimension / Redimension Fast

**Rearranges the nesting order of a recursive structure. `Redimension Fast` uses the built-in `StructureRedimension` for better performance.**

```
Structure::Redimension Fast = Func(
    Structure( &Data ),
    Array( Dimensions ),
    Array( Redimension To ),
)
Returns( Structure() )
```

---

### Structure::Recursive Redim

**Remaps keys in a tree structure using an index array.**

```
Structure::Recursive Redim = Func(
    Structure( Input ),
    Array( Key Map ),
    Double( Sum Results )    := True,
    Double( Ignore Errors )  := False,
)
Returns( Structure() )
```

---

### Structure::Sum Structure Leaf

**Sums all Double-valued leaves at each branch, collapsing them into a single total.**

```
Structure::Sum Structure Leaf = Func(
    Any( X ),
)
Returns( Any() )
```

---

### Structure::Extreme Element

**Returns the key of the extreme (max/min) element in a structure.**

```
Structure::Extreme Element = Func(
    ComponentValueStructure( S ),
    Slang( Op ) = Func( A, B ) Return( A > B ),
)
Returns( Any() )
```

---

### Structure::Most Frequent Elements

**Returns a GStructure of the most frequently occurring values, keyed by value, with arrays of matching keys.**

```
Structure::Most Frequent Elements = Func(
    Structure( S ),
)
Returns( GStructure() )
```

---

### Structure::Sprintf

**Formats a string using `%<Key>` placeholders substituted from a structure.**

```
Structure::Sprintf = Func(
    String( Format ),
    Structure( Struct ),
    String( Space Replacement Char ) := " ",
)
Returns( String() )
```

```slang
@Structure::Sprintf( "%<Book>:%<Group>", {| Book := 101, Group := "IRP" |} );
// "101:IRP"
```

---

### Structure::Extend

**Projection operator for a collection of structures: adds a new computed column.**

```
Structure::Extend = Func(
    SubscriptableDatatype( Structs ),
    Slang( F ),
    Any( New Key ),
)
Returns( SubscriptableDatatype() )
```

---

### Structure::Project

**Projection operator: keeps only the specified columns (or removes them with `AllBut`).**

```
Structure::Project = Func(
    SubscriptableDatatype( Structs ),
    Array( Keys ),
    Double( AllBut ) := False,
)
Returns( SubscriptableDatatype() )
```

---

### Structure::KeyValApply InPlace

**Recursively walks a structure, applying a function to each key-value pair.
If the function returns True, the entry is deleted.**

```
Structure::KeyValApply InPlace = Func(
    Any( &S ),
    Slang( F ),
    Double( Apply To Structures ) := False,
    Double( Down First )          := False,
)
Returns()
```

---

### Structure::Apply At Level

**Like `ValApply` but applied at a specified depth level in a nested structure.**

```
Structure::Apply At Level = Func(
    ComponentValueStructure( S ),
    Double( Level ),
    Slang( F ),
)
Returns( ComponentValueStructure() )
```

---

### Structure::Iterate Deep

**Traverses a nested structure and calls `Call Back( Path, Value )` for every leaf.**

```
Structure::Iterate Deep = Func(
    ComponentValueStructure( Structure ),
    Slang( Call Back ),
    Array( Path ) = [],
)
Returns()
```

---

### Structure::Replace Leaves or Keys with

**Recursively searches for `Replace` in both keys and values, replacing with `With`. Handles structures, arrays, curves, and typed structures.**

```
Structure::Replace Leaves or Keys with = Func(
    SubscriptableDatatype( &S ),
    Any( Replace ),
    Any( With ),
    Double( Throw on Invalid Key )                         := False,
    Double( Allow SubscriptableDatatype Value Replace )    := False,
)
Returns()
```

---

### Structure::Get Keys

**Collects keys at a specified depth in a nested structure.**

```
Structure::Get Keys = Func(
    Str,
    Double( Depth ),
    Double( Make Unique ) := True,
)
Returns( Array() )
```

---

### Structure::Get All Keys

**Returns all keys of a structure and its sub-structures (flattened, optionally unique).**

```
Structure::Get All Keys = Func(
    StringValueStructure( Str ),
    Double( Make Unique ) := True,
)
Returns( Array() )
```

---

### Structure::Build Parents Tree

**Given `{| Child := Parent, ... |}`, builds a forest of inheritance trees.**

```
Structure::Build Parents Tree = Func(
    Structure( Children ),
)
Returns( Structure() )
```

---

### Structure::Find First Keyword

**Returns the first keyword from a list that exists in the given structure (or Null).**

```
Structure::Find First Keyword = Func(
    Structure( Map ),
    Array( Keyword List ),
)
Returns( String(), Null )
```

---

### Structure::Sample

**Returns at most `n Elements To Keep` entries from the structure (arbitrary selection).**

```
Structure::Sample = Func(
    GrowableStringValueStructure( Structure ),
    Double( n Elements To Keep ),
)
Returns( GrowableStringValueStructure() )
```

---

### Structure::Summarise Strings

**Summarises a structure of strings: shows first key=value plus count of remaining entries.**

```
Structure::Summarise Strings = Func(
    Structure( Struct ),
)
Returns( String() )
```

```slang
@Structure::Summarise Strings( {| "Pear" := "yum", "Peach" := "rum" |} );
// "Peach=rum, +1"
```

---

### Structure::ArrayToGStructure

**Returns a GStructure whose keys are the array elements.**

```
Structure::ArrayToGStructure = Func(
    Array( Array ),
    Any( Init ) = Null,
    Double( Init To Index Value ) := False,
)
Returns( Any() )
```

---

### Structure::Interpolate

**Interpolates a value from a tree of structures of arbitrary dimension. Supports Linear, Closest, PWC (piecewise constant), and Match modes.**

```
Structure::Interpolate = Func(
    Any( Data ),
    Array( Point ),
    Array( DataTypes ),
    Array( StartDates )      := [],
    Array( InterpTypes )     := [],
    Array( FlatExtrap )      := [],
    Date( DefStartDate )     := Date(),
    Double( Return Weights ) := False,
)
Returns( Any(), Error() )
```

---

### Structure::Keys Per Sub Keys

**Given a structure of structures, inverts the nesting: returns each sub-key mapped to the array of parent keys that contain it.**

```
Structure::Keys Per Sub Keys = Func(
    StringValueStructure( Input Struct ),
)
Returns( StringValueStructure() )
```

---

### Structure::ComponentExtractReplaceNull

**Like `ComponentExtract`, but also replaces Null values with the default.**

```
Structure::ComponentExtractReplaceNull = Func(
    ComponentValueStructure( Structure ),
    Any( Component ),
    Any( Default ),
)
Returns( Any() )
```

---
---

# Functions from `_LIB Structure Functions 3`

The functions below live in `_LIB Structure Functions 3`, which is internally linked
by the umbrella `_LIB Structure Functions`.

---

## DiffLossless Family

---

### Structure::DiffLossless

**A full, lossless diff of two values. Reports additions, deletions, and changes.
For changes, returns both the "Old" and "New" values.
Recursively drills into structures, arrays, curves, GCurves, and typed structures.**

```
Structure::DiffLossless = Func(
    X,
    Y,
    Double( Tolerance )                             := 0,
    Double( Time Tolerance )                        := 0,
    Double( Tds Tolerance )                         := Error Value,
    Date( Curve Diff High Limit )                   := HighLimit( "Date" ),
    String( LabelX )                                := "",
    String( LabelY )                                := "",
    Double( Allow Typed Structs, Spec::Boolean() )  := True,
    Double( TS Members Only, Spec::Boolean() )      := False,
    Double( Relative, Spec::Boolean() )             := False,
    Structure( Type Comparator Map )                := {||},
)
Returns( Structure(), Array(), Null )
```

**Key differences from other Diff functions:**

| Function | Coverage | Change shows | Recursive? | Drills into Arrays/Curves? |
|----------|----------|-------------|------------|---------------------------|
| `Diff` | Partial (deletions/changes from X) | Just X's value | Optional | No |
| `AllDiffs` | Full (add/del/change) | Just X's value | Yes | No |
| `Diff Symmetric` | Differences on both sides | Both values | Optional | No |
| **`DiffLossless`** | **Full** | **Both Old and New** | **Yes** | **Yes** |

The result can be applied: `@Structure::DiffLossless Apply( &X, Diff )` yields Y.

---

### Structure::DiffLossless Apply

**Applies a lossless diff to a structure, reconstructing the target state.**

```
Structure::DiffLossless Apply = Func(
    &X,
    Diff,
    Double( Strict, Spec::Boolean() )           = True,
    Double( TS Members Only, Spec::Boolean() )  := False,
)
Returns()
```

---

### Structure::DiffLossless Invert

**Inverts a lossless diff: swaps "Added"/"Deleted" and "Old"/"New" so applying
the inverted diff to Y yields X.**

```
Structure::DiffLossless Invert = Func(
    Diff,
)
Returns( Structure(), Array(), Null )
```

---

### Structure::DiffLossless Flatten

**Flattens a hierarchical lossless diff into a structure with `Added`, `Deleted`, and `Changed` GStructures, each keyed by the path array. This makes it easier to convert into reports.**

```
Structure::DiffLossless Flatten = Func(
    Diff,
)
Returns( Structure(), Null )
```

---

### Structure::DiffLossless Flatten Apply

**Like `DiffLossless Apply`, but operates on flattened diffs (as produced by `DiffLossless Flatten` or `DiffLossless Conflicts`).**

```
Structure::DiffLossless Flatten Apply = Func(
    &X,
    Diff,
)
Returns()
```

---

### Structure::DiffLossless Conflicts

**Three-way merge conflict detection. Given a `Base`, `New1`, and `New2`, identifies:
`Common` changes, changes unique to `Change1` / `Change2`, and `Conflict`s.**

```
Structure::DiffLossless Conflicts = Func(
    Structure( Base ),
    Structure( New1 ),
    Structure( New2 ),
    Double( Tolerance ) := 0,
)
Returns( Structure() )
```

Returns `{| Conflict := GStructure(), Common := Structure(), Change1 := Structure(), Change2 := Structure() |}`.

---

### Structure::Sort From Deep

**Sorts top-level keys of a structure by values found at a deep nested path.**

```
Structure::Sort From Deep = Func(
    Structure( Struct ),
    Array( Sort Key Path ),
    Array( SortTable Arg ),
    Double( Strict )         := False,
    Double( Max Duplicates ) := 10,
)
Returns( Array() )
```

---

### Structure::Sprintf

**Returns formatted string with `%<Key>` placeholders substituted from a structure.** (Also in Lib 3.)

```
Structure::Sprintf = Func(
    String( Format ),
    Structure( Struct ),
    String( Space Replacement Char ) := " ",
)
Returns( String() )
```
