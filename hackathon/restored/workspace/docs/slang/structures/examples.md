# Structure Functions -- Examples

Examples extracted from the production test suites:
- `Test: Structure Fns 1` (tests `_LIB Structure Functions 1`)
- `Test: Structure Fns 2` (tests `_LIB Structure Functions 2`)
- `Test: Structure Fns 3` (tests `_LIB Structure Functions 3`)

All examples require:

```slang
Link( "_LIB Structure Functions" );
```

---

## Table of Contents

- [Flatten / Reshape / Unflatten](#flatten--reshape--unflatten)
- [To Array of Array / From Array Of Array](#to-array-of-array)
- [Intersection](#intersection)
- [ExtractSimple / Extract](#extraction)
- [Map / SMap](#map--smap)
- [Filter](#filter)
- [Compare to Depth](#compare-to-depth)
- [StructToArrayOfStruct / StructOfArrayToArrayOfStruct](#struct-array-conversions)
- [StructToSingletonStructs / SingletonStructsToStruct](#singleton-structs)
- [ForEachKeyVal / KeyVal Mapcar / KeyVal Foldl](#iteration-map-fold)
- [PruneZero](#prune-zero)
- [Diff / AllDiffs](#diff--alldiffs)
- [Diff Symmetric](#diff-symmetric)
- [DiffLossless](#difflossless)
- [As Single Line String / Print Simple](#display)
- [Add Deep Entry / Entry](#deep-entry)
- [Set By Path / Get By Path](#set-get-by-path)
- [Apply to Leaves / Transform Leaves](#apply-to-leaves)
- [Apply to Keys](#apply-to-keys)
- [Rename Components](#rename-components)
- [Sorted by Values / Sorted by Keys](#sorting)
- [Invert / InvertSimple](#invert)
- [Invert Structure Of Structures](#invert-structure-of-structures)
- [StructureCaseToStructure](#structurecasetostructure)
- [CastToStructure](#casttostructure)
- [ArrayOfStructToStruct](#arrayofstructtostruct)
- [Categorize / Categorize As Tree](#categorize)
- [Common Values](#common-values)
- [Destroy By Path](#destroy-by-path)
- [Cross Struct of Array](#cross-struct-of-array)
- [Sum At Each Level](#sum-at-each-level)
- [Extract Values As Array / Extract Value](#extract-values)
- [Filter Dimensions](#filter-dimensions)
- [Cmp Structures](#cmp-structures)
- [Union / StrictUnion](#union)
- [Intersect / Common Values](#intersect--common-values)
- [Group By / Categorize](#group-by--categorize)
- [Aggregate](#aggregate)
- [DiffLossless](#difflossless-advanced)
- [DiffLossless Flatten / Conflicts](#difflossless-flatten--conflicts)
- [Get By Path Deep / Get By Uri Path](#path-access-advanced)
- [Cross Struct of Array / Cartesian Product](#cross-product)
- [Extend / Project](#extend--project)
- [StructOfStructToArrayOfStruct / ArrayOfStructToStructNested](#nested-conversions)
- [Sprintf / One Liner / Summarise Strings](#string-formatting)
- [Bucket / Sample](#bucket--sample)
- [Iterate Deep / KeyValApply InPlace](#deep-iteration)
- [Interpolate](#interpolate)

---

## Flatten / Reshape / Unflatten

### Basic Flatten and Reshape

```slang
Input = {|
    "One" := {|
        "Two" := 12,
        "Three" := {|
            "Four" := {| "Five" := 12345, "Six" := 12346 |},
            "Seven" := 127,
        |},
        "Eight" := 18,
    |},
    "Nine"  := 9,
    "Ten"   := 10,
|};

// Flatten with default delimiter "."
Flat = @Structure::Flatten( Input );
// Flat is a single-level structure with keys like "One.Two", "One.Three.Four.Five", etc.

// Reshape back to original
Reshaped = @Structure::Reshape( Flat );
// Reshaped == Input
```

### Flatten with custom delimiter

```slang
Flat Hash = @Structure::Flatten( Input, Delimiter := "#" );
// Keys: "One#Two", "One#Three#Four#Five", etc.

// Must use same delimiter to reshape
Reshaped Hash = @Structure::Reshape( Flat Hash, Delimiter := "#" );
// Reshaped Hash == Input
```

### Flatten arrays

```slang
S = {| "A" := [ "b", "c", "d" ], "B" := {| "e" := "z" |} |};

// Without array flattening
Flat1 = @Structure::Flatten( S );
// {| "A" := [ "b", "c", "d" ], "B.e" := "z" |}

// With array flattening
Flat2 = @Structure::Flatten( S, Flatten Arrays := True );
// {| "A.0" := "b", "A.1" := "c", "A.2" := "d", "B.e" := "z" |}
```

### Unflatten

```slang
Flat = {| "a" := 1, "b.c" := 2, "b.d" := 3, "b.e.f.g" := 4, "b.e.f.h" := 5 |};
Nested = @Structure::Unflatten( Flat );
// {| "a" := 1, "b" := {| "c" := 2, "d" := 3, "e" := {| "f" := {| "g" := 4, "h" := 5 |} |} |} |}

// Custom delimiter
Flat2 = {| "a" := 1, "b_c" := 2, "b_d" := 3 |};
Nested2 = @Structure::Unflatten( Flat2, Delimiter := "_" );
// {| "a" := 1, "b" := {| "c" := 2, "d" := 3 |} |}
```

---

## To Array of Array

```slang
One Level = {| "A" := 1, "B" := 2, "C" := 3 |};
AOA = @Structure::To Array of Array( One Level );
// [ [ "A", 1 ], [ "B", 2 ], [ "C", 3 ] ]

Two Level = {| "A" := {| "B" := 1, "C" := 2 |}, "D" := {| "E" := 1, "F" := 2 |} |};
AOA2 = @Structure::To Array of Array( Two Level );
// [ [ "A", "B", 1 ], [ "A", "C", 2 ], [ "D", "E", 1 ], [ "D", "F", 2 ] ]

// Include empty paths
S = {| "A1" := {| "B1" := 1 |}, "A2" := {||}, "A3" := {| "B2" := {| "C1" := "yo" |} |} |};
AOA3 = @Structure::To Array of Array( S, Include Empty Paths := True );
// [ [ "A1", "B1", 1 ], [ "A2", {||} ], [ "A3", "B2", "C1", "yo" ] ]

// Round-trip back to structure
Back = @Structure::From Array Of Array( AOA3 );
// Back == S
```

---

## Intersection

```slang
A = {| "Only in A" := 1, "Common" := 123, "Also Common" := "ABC" |};
B = {| "Only in B" := 2, "Common" := 231, "Also Common" := "BCA" |};

Result = @Structure::Intersection( A, B );
// {| "Common" := Null, "Also Common" := Null |}

// Types must match
Result2 = @Structure::Intersection( Structure(), StructureCase() );
// Null
```

---

## Extraction

### ExtractSimple

```slang
S = {| "a" := 1, "b" := 2, "c" := 3 |};
Sub = @Structure::ExtractSimple( S, [ "a", "c" ] );
// {| "a" := 1, "c" := 3 |}

// Works on GStructure too
G = GStructure( 1, "a", 2, "b", 3, "c" );
SubG = @Structure::ExtractSimple( G, [ 1, 3 ] );
// GStructure( 1, "a", 3, "c" )
```

### Extract (destructive when by-ref)

```slang
S = {| "A" := 1, "B" := 2, "C" := 3 |};
Extracted = @Structure::Extract( S, [ "B", "C" ] );
// {| "B" := 2, "C" := 3 |}

// With default for missing keys
Extracted2 = @Structure::Extract( S, [ "B", "C", "D" ], 0, 0 );
// {| "B" := 2, "C" := 3, "D" := 0 |}

// Destructive extract (modifies original)
Ref = {| "a" := 1, "b" := 2 |};
Pulled = @Structure::Extract( &Ref, [ "a" ] );
// Pulled == {| "a" := 1 |}, Ref == {| "b" := 2 |}
```

---

## Map / SMap

```slang
// Build structure from keys by applying a function
Result = @Structure::Map( [ "a", "b", "c" ], \x -> Asc( StrLower( x ) ) );
// {| "a" := 97, "b" := 98, "c" := 99 |}

// StructureCase output
Result2 = @Structure::Map( [ "a", "b" ], \x -> Asc( x ), Case := True );
// {\ "a" := 97, "b" := 98 \}

// GStructure output
Result3 = @Structure::Map( [ 12, 7 ], \x -> x + 1, G := True );
// GStructure( 7, 8, 12, 13 )

// SMap re-maps an existing structure's values
G = GStructureFromKeys( [ "a", "b" ], [ 1, 1 ] );
Remapped = @Structure::SMap( G, \x -> x + 1 );
// GStructure( "a", result_of_f("a"), "b", result_of_f("b") )
```

---

## Filter

```slang
S = {| "A" := 1, "B" := 0, "C" := 3 |};

// Filter by value (truthy)
Result = @Structure::Filter( S );
// {| "A" := 1, "C" := 3 |}

// Filter by key
Result2 = @Structure::Filter( S, \k -> k != "b", Filter by Keys := True );
// {| "A" := 1, "C" := 3 |}  (keys are case-insensitive, "b" matches "B")

// FilterSimple (no recursion, faster)
Result3 = @Structure::FilterSimple( S, \v -> v > 0 );
// {| "A" := 1, "C" := 3 |}
```

---

## Compare to Depth

```slang
X1 = {| "a" := {| "a1" := 1, "a2" := {| "c3" := 3, "c4" := 4 |} |},
        "b" := {| "b1" := 1, "b2" := {| "c3" := 3, "c4" := 4 |} |} |};

// Same structure, different value at depth 4
X5 = {| "a" := {| "a1" := 1, "a2" := {| "c3" := 3, "c4" := 5 |} |},
        "b" := {| "b1" := 1, "b2" := {| "c3" := 3, "c4" := 4 |} |} |};

@Structure::Compare to Depth( X1, X5, 0 );  // True  (depth 0 always True)
@Structure::Compare to Depth( X1, X5, 1 );  // True  (same top-level keys)
@Structure::Compare to Depth( X1, X5, 3 );  // True  (same down to depth 3)
@Structure::Compare to Depth( X1, X5, 4 );  // False (c4 differs at depth 4)
```

---

## Struct-Array Conversions

### StructToArrayOfStruct

```slang
S = {| "Foo1" := [ 1, 2, 3 ], "Foo2" := [ "A", "B" ] |};
Result = @Structure::StructToArrayOfStruct( S, "Key_Name_X", "Value_Name_X" );
// [
//   {| "Key_Name_X" := "Foo1", "Value_Name_X" := [ 1, 2, 3 ] |},
//   {| "Key_Name_X" := "Foo2", "Value_Name_X" := [ "A", "B" ] |},
// ]
```

### StructOfArrayToArrayOfStruct

```slang
S = {| "a" := [ 1, 2 ], "b" := [ 3, 4 ] |};
Result = @Structure::StructOfArrayToArrayOfStruct( S );
// [ {| "a" := 1, "b" := 3 |}, {| "a" := 2, "b" := 4 |} ]
```

---

## Singleton Structs

### StructToSingletonStructs

```slang
S = {| "a" := 1, "b" := 2 |};
Singletons = @Structure::StructToSingletonStructs( S );
// [ {| "a" := 1 |}, {| "b" := 2 |} ]

// Works with GStructure and StructureCase too
G = GStructure( [ "a", "b" ], 1, [ "b", "a" ], 2 );
GS = @Structure::StructToSingletonStructs( G );
// [ GStructure( [ "a", "b" ], 1 ), GStructure( [ "b", "a" ], 2 ) ]
```

---

## Iteration, Map, Fold

### ForEachKeyVal

```slang
S = {| "A" := 1, "B" := 2 |};
Result = @Structure::ForEachKeyVal( S, \x, y -> Sprint( x, " ", y ) );
// [ "a 1", "b 2" ]

// GStructure
G = GStructure( 1, 1 );
Result2 = @Structure::ForEachKeyVal( G, \x, y -> x + y );
// [ 2 ]
```

### KeyVal Mapcar

```slang
Result = @Structure::KeyVal Mapcar( \x, y -> Sprint( x, " ", y ), {| "A" := 1, "B" := 2 |} );
// {| "a" := "a 1", "b" := "b 2" |}

// StructureCase preserves case
Result2 = @Structure::KeyVal Mapcar( \x, y -> Sprint( x, " ", y ), {\ "A" := 1, "B" := 2 \} );
// {\ "A" := "A 1", "B" := "B 2" \}

// Works on arrays too (key = index)
Result3 = @Structure::KeyVal Mapcar( \x, y -> x * y, [ 1, 1, 1, 1 ] );
// [ 0, 1, 2, 3 ]
```

### KeyVal Foldl

```slang
Result = @Structure::KeyVal Foldl(
    \x, y, accum -> Sprint( accum, x, y, "," ),
    "",
    {| "A" := 1, "B" := 2 |},
    Commutative := False
);
// "a1,b2,"

// Accumulate structure values into an array
Result2 = @Structure::KeyVal Foldl(
    \_, y, accum -> accum ++ y,
    [],
    {| "A" := [ 1, 2 ], "B" := [ 3, 4 ] |},
    Commutative := False
);
// [ 1, 2, 3, 4 ]
```

---

## Prune Zero

```slang
S = {|
    "Z" := 0,
    "One" := {|
        "AZ" := 1e-10,
        "NZ" := 1e-5,
        "Two" := 12,
        "Z" := 0,
    |},
    "Nine" := 9,
|};

Pruned = S;
@Structure::PruneZero( &Pruned );
// Pruned: Z removed, One.Z removed, One.AZ kept (not exactly 0)

// With threshold
Pruned2 = S;
@Structure::PruneZero( &Pruned2, False, 1e-8 );
// Pruned2: additionally removes One.AZ (1e-10 <= 1e-8)

// With KeysToSkip
Pruned3 = S;
@Structure::PruneZero( &Pruned3, KeysToSkip := [ "Z" ] );
// Pruned3: top-level Z and One.Z are NOT removed (skipped)
```

---

## Diff / AllDiffs

### Structure::Diff

```slang
X = {| "A" := 1, "B" := 2, "C" := 3 |};
Y = {| "A" := 1, "B" := 99 |};

D = @Structure::Diff( X, Y );
// {| "B" := 2, "C" := 3 |}  (B differs, C missing from Y)
```

### Structure::AllDiffs

```slang
X = {| "A" := 1, "B" := 2, "C" := 3 |};
Y = {| "A" := 2, "B" := 3, "C" := 3 |};

// Ignore "A", compare everything else
D = @Structure::AllDiffs( X, Y, TagsToIgnore := [ "A" ] );
// {| "B" := 2 |}

// Ignore tags recursively in sub-structures
Sub1 = {| "D" := 4, "E" := 5, "F" := 6 |};
Sub2 = {| "D" := 4, "E" := 7, "F" := 6 |};
Stru1 = {| "A" := 1, "B" := Sub1, "C" := 3 |};
Stru2 = {| "A" := 2, "B" := Sub2, "C" := 3 |};

Result = @Structure::AllDiffs( Stru1, Stru2,
    TagsToIgnore := [ "A", "E" ],
    Ignore Tags Recursively := True
);
// {||} -- empty, both "A" and "E" ignored at all levels
```

---

## Diff Symmetric

```slang
S1 = {|
    "A" := {| "B" := 2, "C" := 3 |},
    "B" := 2,
    "D" := 4,
|};
S2 = {|
    "A" := {| "B" := 3, "C" := 3, "D" := 3 |},
    "C" := 3,
    "D" := 4,
|};

Diffs = @Structure::Diff Symmetric( S1, S2 );
// {|
//   "A" := {|
//       "B" := {| "S1" := 2, "S2" := 3 |},
//       "D" := {| "S2" := 3 |}
//   |},
//   "B" := {| "S1" := 2 |},
//   "C" := {| "S2" := 3 |}
// |}
```

---

## DiffLossless

```slang
X = {| "A" := 1, "B" := [ 0, 1, 2 ], "D" := {| "A" := 1, "B" := [ 1 ] |} |};
Y = {| "A" := 1.01, "B" := [ 0.01, 1, 2 ], "D" := {| "A" := 1.001, "B" := [ 1.001 ] |} |};

// Compute lossless diff
Diff = @Structure::DiffLossless( X, Y );

// Apply diff to transform X into Y
X1 = X;
@Structure::DiffLossless Apply( &X1, Diff );
// X1 == Y

// Invert diff to go from Y back to X
Inverted = @Structure::DiffLossless Invert( Diff );
Y1 = Y;
@Structure::DiffLossless Apply( &Y1, Inverted );
// Y1 == X

// Self-diff is always Null
@Structure::DiffLossless( X, X );   // Null
```

---

## Display

### As Single Line String

```slang
S = {| "blah" := "bleh", "blih" := "bluh", "bloh" := 1.00111 |};

@Structure::As Single Line String( S, Double Flags := _Concise, Double Rounding := 4 );
// "blah=bleh, blih=bluh, bloh=1.0011"

@Structure::As Single Line String( S, Double Flags := _Concise, Double Rounding := 3,
    Tuple Delimiter := "\n" );
// "blah=bleh\nblih=bluh\nbloh=1.001"

// Shorthand notation
S2 = {| "blah" := "bleh", "blih" := {| "bluh" := 2.002, "bloh" := 1.001 |} |};
@Structure::As Single Line String( S2, Double Flags := _Concise, Double Rounding := 3,
    Shorthand := True, Recursive := True );
// "{| blah:=bleh, blih:={| bloh:=1.001, bluh:=2.002 |} |}"
```

### Print Simple

```slang
S = {| "a" := 100, "b" := "Hello" |};
@Structure::Print Simple( S );
// Prints: a=100, b=Hello
```

---

## Deep Entry

### Add Deep Entry

```slang
S = {||};

// Replace (default)
@Structure::Add Deep Entry( &S, [ "Level1", "Level2", "Value" ], 123 );
// S == {| "Level1" := {| "Level2" := {| "Value" := 123 |} |} |}

// Append to array
S2 = {| "Level1" := {| "Values" := [ 1, 2 ] |} |};
@Structure::Add Deep Entry( &S2, [ "Level1", "Values" ], 3, Op := "Append" );
// S2.Level1.Values == [ 1, 2, 3 ]

// Add (arithmetic)
S3 = {| "Level1" := {| "Values" := 1 |} |};
@Structure::Add Deep Entry( &S3, [ "Level1", "Values" ], 2, Op := "Add" );
// S3.Level1.Values == 3

// Set If Missing
S4 = {| "Level1" := 1 |};
@Structure::Add Deep Entry( &S4, [ "Level1" ], 2, Op := "Set If Missing" );
// S4.Level1 == 1 (unchanged, already had a value)

// Unique (throws if already set)
S5 = {||};
@Structure::Add Deep Entry( &S5, [ "Level1" ], 1, Op := "Unique" );
// S5 == {| "Level1" := 1 |}
// @Structure::Add Deep Entry( &S5, [ "Level1" ], 2, Op := "Unique" );  // THROWS!
```

### Structure::Entry

```slang
// Change existing entry via pointer
A = [ 0, {| "b" := [ 0, 2 ] |} ];
*@Structure::Entry( &A, [ 1, "b", 1 ] ) = 3;
// A[1].b[1] is now 3

// Test for existence
A = {| "X" := {| "Y" := 1 |} |};
Exists = !IsError( @Structure::Entry( &A, [ "X", "Y" ] ) );      // True
Missing = !IsError( @Structure::Entry( &A, [ "X", "Z" ] ) );      // False

// Create new entries with append (-1)
A = {||};
*@Structure::Entry( &A, [ "X", -1 ], [] ) = 5;
*@Structure::Entry( &A, [ "X", -1 ], [] ) = 4;
*@Structure::Entry( &A, [ "X", -1 ], [] ) = 3;
// A == {| "X" := [ 5, 4, 3 ] |}
```

---

## Set / Get By Path

```slang
S = Structure();
@Structure::Set By Path( &S, [ "A", "B", "C" ], 1 );
@Structure::Set By Path( &S, [ "A", "B", "D" ], 2 );
@Structure::Set By Path( &S, [ "A", "Q", "D" ], 3 );
@Structure::Set By Path( &S, [ "A", "B", "D" ], 4 );  // overwrites previous

// Get by path
Val = @Structure::Get By Path( &S, [ "A", "Q", "D" ] );
// Val == 3

// Get with default for missing path
Val2 = @Structure::Get By Path( &S, [ "A", "Q", "foo" ], Default := "Hello" );
// Val2 == "Hello"

// Returns Null on missing (instead of throwing)
Val3 = @Structure::Get By Path( &S, [ "A", "Q", "foo" ],
    Default := "Hello",
    Return Null on Missing Component := True
);
// Val3 == Null
```

---

## Apply to Leaves

```slang
S = {| "A" := 1, "B" := {| "C" := 2, "D" := 3 |} |};
Expected = {| "A" := 2, "B" := {| "C" := 4, "D" := 8 |} |};

// In-place modification
@Structure::Apply to Leaves( &S, Func( x ) Pow( 2, x ) );
// S == Expected

// Non-destructive transform
S2 = {| "A" := 1, "B" := {| "C" := 2, "D" := 3 |} |};
Result = @Structure::Transform Leaves( S2, Func( x ) Pow( 2, x ) );
// Result == Expected, S2 unchanged

// Recurse into arrays
S3 = {| "A" := 1, "B" := [ {| "C" := 2, "D" := 3 |} ] |};
Result2 = @Structure::Transform Leaves( S3,
    Func( x ) If( TypeOf( x ) == "Double" ) Pow( 2, x ) : x,
    Recurse Arrays := True
);
// {| "A" := 2, "B" := [ {| "C" := 4, "D" := 8 |} ] |}
```

---

## Apply to Keys

```slang
S = {| "A" := 1, "B" := {| "C" := 2, "D" := 3 |} |};
Result = @Structure::Apply to Keys( S, Func( x ) x + "Z" );
// {| "AZ" := 1, "BZ" := {| "CZ" := 2, "DZ" := 3 |} |}

// Depth-limited
Result2 = @Structure::Apply to Keys( S, Func( x ) x + "Z", Depth := 1 );
// {| "AZ" := 1, "BZ" := {| "C" := 2, "D" := 3 |} |}

// With aggregation function (merge keys that become identical)
S2 = {| "A,1" := {| "C" := 5 |}, "A,2" := {| "D" := 3 |} |};
Result3 = @Structure::Apply to Keys( S2,
    Func( x ) StrSplit( x, "," )[0],
    Agg Func := Func( x, y ) x + y
);
// {| "A" := {| "C" := 5, "D" := 3 |} |}
```

---

## Rename Components

```slang
Structs = [
    {| "Foo1" := "Bar1", "Foo2" := "Bar2", "Foo3" := "Bar3" |},
];
Mapping = {| "Foo1" := "Fie1", "Foo2" := "Fie2", "Foo3" := "Fie3" |};

Result = @Structure::Rename Components( Structs, Mapping );
// [ {| "Fie1" := "Bar1", "Fie2" := "Bar2", "Fie3" := "Bar3" |} ]

// Single structure
Result2 = @Structure::Rename Components Single(
    {| "Foo1" := "Bar1", "Foo2" := "Bar2" |},
    {| "Foo1" := "Fie1" |}
);
// {| "Fie1" := "Bar1", "Foo2" := "Bar2" |}
```

---

## Sorting

### Sorted by Values

```slang
S = {| "A" := 0, "B" := 13, "C" := 2 |};
@Structure::Sorted by Values( S );
// [ [ "A", 0 ], [ "C", 2 ], [ "B", 13 ] ]

// Descending
@Structure::Sorted by Values( S, Func( a, b ) b <=> a );
// [ [ "B", 13 ], [ "C", 2 ], [ "A", 0 ] ]
```

### Sorted by Values Deep

```slang
S = {| "a" := {| "b" := 1, "c" := -2 |}, "d" := 0.5 |};
@Structure::Sorted by Values Deep( S );
// [ [ [ "a", "c" ], -2 ], [ [ "d" ], 0.5 ], [ [ "a", "b" ], 1 ] ]
```

### Sorted by Keys

```slang
S = {| "C" := 2, "A" := 0, "B" := 13 |};
@Structure::Sorted by Keys( S );
// [ [ "A", 0 ], [ "B", 13 ], [ "C", 2 ] ]
```

---

## Invert

```slang
Normal = {| "a" := 1, "b" := 2, "c" := 3 |};

// Default: values become arrays (supports one-to-many)
@Structure::Invert( Normal );
// {| "1" := [ "a" ], "2" := [ "b" ], "3" := [ "c" ] |}

// One to One: values are scalars
@Structure::Invert( Normal, One to One := True );
// {| "1" := "a", "2" := "b", "3" := "c" |}

// Duplicate values with One to One throws
Problematic = {| "a" := 1, "b" := 1, "c" := 2 |};
// @Structure::Invert( Problematic, One to One := True );  // THROWS!

// Ignore duplicates silently
@Structure::Invert( Problematic, One to One := True, Ignore Duplicates := True );
// {| "1" := "a", "2" := "c" |}
```

---

## Invert Structure Of Structures

```slang
X = {| "a" := {| "x" := 1, "y" := 2 |}, "b" := {| "x" := 10, "z" := 20 |} |};
Y = @Structure::Invert Structure Of Structures( X );
// Y == {| "x" := {| "a" := 1, "b" := 10 |}, "y" := {| "a" := 2 |}, "z" := {| "b" := 20 |} |}

// Reversible
@Structure::Invert Structure Of Structures( Y );
// == X
```

---

## StructureCaseToStructure

```slang
SC = StructureCase( "Alpha", 99, "Bravo", [ StructureCase( "Charlie", StructureCase( "Delta", 2 ) ) ] );
Result = @Structure::StructureCaseToStructure( SC );
// Structure( "Alpha", 99, "Bravo", [ Structure( "Charlie", Structure( "Delta", 2 ) ) ] )
```

---

## CastToStructure

```slang
Nested = {| "A" := [ GStructure( 1, "B" ) ] |};

// Deep cast
Result = @Structure::CastToStructure( Nested, Deep := True );
// {| "A" := {| "0" := {| "1" := "B" |} |} |}

// With GStructure output
Result2 = @Structure::CastToStructure( Nested, Deep := True, Use GStructure := True );
// GStructure( "A", GStructure( 0, GStructure( 1, "B" ) ) )

// With Prev DataType Key (tracks original types)
G = GStructure( 0, "A", 1, [ "Foo" ] );
Result3 = @Structure::CastToStructure( G, Prev DataType Key := "PDK", Deep := True );
// {| "PDK" := "GStructure", "0" := "A", "1" := {| "PDK" := "Array", "0" := "Foo" |} |}

// Dont Convert Types
Result4 = @Structure::CastToStructure(
    {| "Foo" := [ 2 ] |},
    Dont Convert Types := [ "Array" ],
    Deep := True
);
// {| "Foo" := [ 2 ] |}  (array left alone)
```

---

## ArrayOfStructToStruct

```slang
Table = [
    {| "Key" := "The",   "Value a" := "quick",    "Value b" := "Brown fox" |},
    {| "Key" := "Jumps",  "Value a" := "over the", "Value b" := "lazy dog"  |},
];

// Default: Structure, keys stringified, tag removed from values
Result = @Structure::ArrayOfStructToStruct( Table, "Key" );
// {| "The" := {| "Value a" := "quick", "Value b" := "Brown fox" |},
//    "Jumps" := {| "Value a" := "over the", "Value b" := "lazy dog" |} |}

// Keep tag in values
Result2 = @Structure::ArrayOfStructToStruct( Table, "Key", RemoveTag := False );
// Values also contain "Key" component

// Case-sensitive keys
CS = [
    StructureCase( "Key", "A", "V", "Foo" ),
    StructureCase( "Key", "a", "V", "Bar" ),
];
Result3 = @Structure::ArrayOfStructToStruct( CS, "Key", True, True, TagCaseSensitive := True );
// StructureCase with keys "a" and "A"
```

---

## Categorize

```slang
// Categorize by value
Categorized = @Structure::Categorize( [ "One", "Four", "Two" ], \_, Y -> Size( Y ) );
// GStructure( 3, [ "One", "Two" ], 4, [ "Four" ] )

// Categorize by index
Categorized2 = @Structure::Categorize( [ "Zero", "One", "Two" ], \X, _ -> Mod( X, 2 ) );
// GStructure( 0, [ "Zero", "Two" ], 1, [ "One" ] )

// Into Structure (case-insensitive keys collapse)
Categorized3 = @Structure::Categorize( [ "One", "one", "ONE" ], \_, Y -> Y, Structure() );
// {| "One" := [ "One", "one", "ONE" ] |}

// Into StructureCase (case-sensitive)
Categorized4 = @Structure::Categorize( [ "One", "one", "ONE" ], \_, Y -> Y, StructureCase() );
// {\ "One" := [ "One" ], "one" := [ "one" ], "ONE" := [ "ONE" ] \}
```

---

## Common Values

```slang
Animals = [
    StructureCase( "Animal", "Cow",     "Type", "Herbivore", "Legs", 4,
        "Classification", StructureCase( "Class", "Mammalia", "Family", "Bovidae" ) ),
    StructureCase( "Animal", "Giraffe", "Type", "Herbivore", "Legs", 4,
        "Classification", StructureCase( "Class", "Mammalia", "Family", "Giraffidae" ) ),
    StructureCase( "Animal", "Camel",   "Type", "Herbivore", "Legs", 4,
        "Classification", StructureCase( "Class", "Mammalia", "Family", "Camelidae" ) ),
];

Result = @Structure::Common Values( Animals, Deep := True );
// StructureCase( "Type", "Herbivore", "Legs", 4,
//   "Classification", StructureCase( "Class", "Mammalia" ) )
// "Animal" and "Family" excluded (differ between entries)
```

---

## Destroy By Path

```slang
S = {| "Good Root" := {| "Good Label" := "Content" |} |};
@Structure::Destroy By Path( &S, [ "Good Root", "Good Label" ] );
// S == {| "Good Root" := {||} |}

// With Clean Up Empty Paths (removes empty parents)
S2 = {| "Good Root" := {| "Good Label" := "Content" |} |};
@Structure::Destroy By Path( &S2, [ "Good Root", "Good Label" ], Clean Up Empty Paths := True );
// S2 == {||}

// Destroy array element
S3 = {| "Root" := {| "List" := [ "Foo", "Bar", "Baz" ] |} |};
@Structure::Destroy By Path( &S3, [ "Root", "List", 1 ],
    Clean Up Empty Paths := True,
    Clean Array Elements := True
);
// S3 == {| "Root" := {| "List" := [ "Foo", "Baz" ] |} |}
```

---

## Cross Struct of Array

```slang
Input = {|
    "x" := [ 1, 2, 3 ],
    "y" := [ "a", "b" ],
    "z" := [ "p", "q" ],
|};

Result = @Structure::Cross Struct of Array( Input, Sorted Order := True );
// Produces all 12 combinations (3 x 2 x 2):
// [ {| x := 1, y := "a", z := "p" |},
//   {| x := 1, y := "a", z := "q" |},
//   {| x := 1, y := "b", z := "p" |},
//   ... etc
// ]
```

---

## Sum At Each Level

```slang
S = {| "X" := 1, "Y" := {| "Z" := 2, "X" := 3 |}, "Z" := -2 |};
Result = @Structure::Sum At Each Level( S );
// {| "X" := 1, "Y" := {| "Z" := 2, "X" := 3, "Total" := 5 |}, "Z" := -2, "Total" := 4 |}

// Custom total key
Result2 = @Structure::Sum At Each Level( S, Total Key := "_SUM_" );
// Uses "_SUM_" instead of "Total"

// Absolute sum
Result3 = @Structure::Sum At Each Level( S, Absolute Sum := True );
// Total := 8 (uses Abs values: 1 + 5 + 2 = 8)
```

---

## Extract Values

### Extract Values As Array

```slang
S = {| "Foo1" := 1, "Foo2" := 2, "Foo3" := 3, "Foo4" := 4 |};

@Structure::Extract Values As Array( S, [ "Foo4", "Foo2" ] );
// [ 4, 2 ]

// Missing keys return Null (or a default)
@Structure::Extract Values As Array( S, [ "Foo3", "X", "Foo1" ] );
// [ 3, Null, 1 ]

@Structure::Extract Values As Array( S, [ "X", "Y" ], [ "Default" ] );
// [ [ "Default" ], [ "Default" ] ]
```

### Extract Value

```slang
S = {| "Foo1" := 2, "Foo2" := 5, "Foo3" := 5, "Foo4" := 10 |};

@Structure::Extract Value( S, 5 );
// {| "Foo2" := 5, "Foo3" := 5 |}

@Structure::Extract Value( S, 0 );
// {||}  (no matches)
```

---

## Filter Dimensions

```slang
S = {|
    "EUR" := {|
        "Cash" := {| "1m" := 20, "2m" := 30 |},
        "Swap" := {| "2y" := 200 |},
    |},
    "GBP" := {|
        "Swap" := {| "2y" := 100, "5y" := 200 |},
        "Cash" := {| "2y" := 20 |},
    |},
|};

// Filter: any currency, Swap only, 2y only
Filter = [ Null, "Swap", "2y" ];
Filtered = @Structure::Filter Dimensions( S, Filter );
// {| "EUR" := {| "Swap" := {| "2y" := 200 |} |},
//    "GBP" := {| "Swap" := {| "2y" := 100 |} |} |}

// Filter Out: everything except the filter
Remaining = @Structure::Filter Out Dimensions( S, Filter );
// Contains Cash entries and Swap.5y

// The two add up to the original
// Filtered + Remaining == S
```

---

## Cmp Structures

```slang
A = {| "Key" := "Value" |};
B = {| "Key" := "Value" |};
@Structure::Cmp Structures( A, B );    // 0 (identical)

A = {| "Key" := "Value" |};
B = {| "Key" := "Value", "Key2" := "Value2" |};
@Structure::Cmp Structures( A, B );    // 1 (B has extra key)

A = {| "Key" := "Value" |};
B = {| "Key1" := "Value" |};
@Structure::Cmp Structures( A, B );    // 2 (completely different keys)
```

---

## Union

```slang
// Basic Union -- overrides go FIRST (left side wins)
Base = {| A := 1, B := 2 |};
Overrides = {| B := 99, C := 3 |};
@Structure::Union( Overrides, Base );
// {| A := 1, B := 99, C := 3 |}

// Multiple arguments
@Structure::Union( {| X := 1 |}, {| Y := 2 |}, {| Z := 3 |} );
// {| X := 1, Y := 2, Z := 3 |}

// StrictUnion -- throws if same key has different values
@Structure::StrictUnion( {| A := 1, B := 2 |}, {| B := 2, C := 3 |} );
// {| A := 1, B := 2, C := 3 |}   (OK because B==2 in both)

// Union Deep -- deep merge with collision resolver
L = {| A := {| X := 1 |} |};
R = {| A := {| X := 2, Y := 3 |} |};
@Structure::Union Deep( L, R );
// {| A := {| X := [ 1, 2 ], Y := 3 |} |}  (collision creates array)
```

---

## Intersect / Common Values

```slang
A = {| A := 1, B := 2, C := 3 |};
B = {| B := 20, C := 30, D := 40 |};

// Intersect: values from A for common keys
@Structure::Intersect( A, B );
// {| B := 2, C := 3 |}

// Keys Intersection: fast, top-level key array
@Structure::Keys Intersection( A, B );
// [ "B", "C" ]

// Common Values across an array of structures
Animals = [
    {\ Type := "Herbivore", Legs := 4, Animal := "Cow"     \},
    {\ Type := "Herbivore", Legs := 4, Animal := "Giraffe" \},
    {\ Type := "Herbivore", Legs := 4, Animal := "Camel"   \},
];
@Structure::Common Values( Animals, Deep := True );
// {\ Type := "Herbivore", Legs := 4 \}
```

---

## Group By / Categorize

```slang
// Group By: group by first character of key
@Structure::Group By(
    {| A1 := 3, A2 := 5, B1 := 4, B2 := 1 |},
    Func( K ) SubStr( K, 0, 0 ),
);
// {| A := [ 3, 5 ], B := [ 4, 1 ] |}

// Group By with custom merge (sum)
@Structure::Group By(
    {\ A1 := 3, A2 := 5, B1 := 4, b2 := 1 \},
    Func( K ) SubStr( K, 0, 0 ),
    Func( X, Y ) X + Y,
    0,
);
// {\ A := 8, b := 1, B := 4 \}

// Categorize: group values by a property
@Structure::Categorize(
    [ "One", "Two", "Four" ],
    \_,Y -> Size( Y ),
);
// GStructure( 3, [ "One", "Two" ], 4, [ "Four" ] )

// Categorize As Tree: preserves key-value structure
Trades = {|
    "T1" := {| Trader := "Jon", Book := "PC" |},
    "T2" := {| Trader := "Amy", Book := "CC" |},
    "T3" := {| Trader := "Jon", Book := "PC" |},
|};
@Structure::Categorize As Tree( Trades, \_,V -> V.Trader );
// GStructure(
//   "Jon", GStructure( "T1", {| Trader := "Jon", Book := "PC" |},
//                      "T3", {| Trader := "Jon", Book := "PC" |} ),
//   "Amy", GStructure( "T2", {| Trader := "Amy", Book := "CC" |} )
// )
```

---

## Aggregate

```slang
// Max across array of structures
Structs = [
    {| A := 1, B := {| C := 5 |} |},
    {| A := 3, B := {| C := 2 |} |},
];
@Structure::Max( Structs );
// {| A := 3, B := {| C := 5 |} |}

// Sum
@Structure::Sum( Structs );
// {| A := 4, B := {| C := 7 |} |}

// Custom aggregation with Slang function
Link( "_LIB String Functions" );
@Structure::Aggregate(
    [ {| A := "X" |}, {| A := "Y" |} ],
    Slang Agg := String::ArrayToString,
);
// {| A := "[ X, Y ]" |}
```

---

## DiffLossless (Advanced)

```slang
// Basic DiffLossless
X = {| A := 1, B := 2, C := 3 |};
Y = {| A := 1, B := 5, D := 4 |};

Diff = @Structure::DiffLossless( X, Y );
// {|
//     Changed := {| B := {| Old := 2, New := 5 |} |},
//     Deleted := {| C := 3 |},
//     Added   := {| D := 4 |},
// |}

// Apply the diff to X to get Y
@Structure::DiffLossless Apply( &X, Diff );
// X is now == Y

// Invert: apply inverted diff to Y to get original X back
X2 = Y;
Inv = @Structure::DiffLossless Invert( Diff );
@Structure::DiffLossless Apply( &X2, Inv );
// X2 == original X

// With tolerance
@Structure::DiffLossless( {| A := 1.0 |}, {| A := 1.0001 |}, Tolerance := 0.001 );
// Null  (within tolerance)
```

---

## DiffLossless Flatten / Conflicts

```slang
// Flatten produces paths as keys in a GStructure
X = {| A := {| B := 1 |}, C := 2 |};
Y = {| A := {| B := 9 |}, C := 2, D := 3 |};
Diff = @Structure::DiffLossless( X, Y );
Flat = @Structure::DiffLossless Flatten( Diff );
// {|
//     Changed := GStructure( [ "A", "B" ], {| Old := 1, New := 9 |} ),
//     Added   := GStructure( [ "D" ], 3 ),
// |}

// Three-way conflict detection
Base = {| A := 1, B := 2 |};
New1 = {| A := 1, B := 3 |};
New2 = {| A := 1, B := 4 |};
Result = @Structure::DiffLossless Conflicts( Base, New1, New2 );
// Result.Conflict has the conflicting paths (B changed to 3 vs 4)
// Result.Common, Result.Change1, Result.Change2 for non-conflicting changes
```

---

## Path Access (Advanced)

### Get By Path Deep

```slang
S = {| A := {| B := {| C := {| D := 1 |} |} |} |};

// Standard Get By Path requires full path from root
@Structure::Get By Path( &S, [ "A", "B", "C", "D" ] );   // 1

// Get By Path Deep searches from anywhere
@Structure::Get By Path Deep( &S, [ "C", "D" ] );   // 1
@Structure::Get By Path Deep( &S, [ "D" ] );         // 1
@Structure::Get By Path Deep( &S, [ "F" ], Default := -1 );  // -1
```

### Get By Uri Path

```slang
Routes = {|
    "users" := {|
        ":id" := {|
            "profile" := "user profile page",
        |},
    |},
|};

Path Params = {||};
@Structure::Get By Uri Path( Routes, [ "users", "42", "profile" ], Path Params := &Path Params );
// Returns "user profile page"
// Path Params == {| id := "42" |}
```

---

## Cross Product

```slang
// Cross Struct of Array
@Structure::Cross Struct of Array(
    {| x := [ 1, 2 ], y := [ "a", "b" ] |},
    Sorted Order := True,
);
// [
//   {| x := 1, y := "a" |}, {| x := 1, y := "b" |},
//   {| x := 2, y := "a" |}, {| x := 2, y := "b" |},
// ]

// Cartesian Product (more flexible)
@Structure::Cartesian Product( {| A := [ 1, 2 ], B := [ 3 ] |} );
// [ {| A := 1, B := 3 |}, {| A := 2, B := 3 |} ]

// With exclusion filter
@Structure::Cartesian Product(
    {| A := [ 0, 1 ], B := [ 2, 3 ] |},
    Exclude Combination := \x -> Mod( x.A + x.B, 2 ) != 0,
);
// [ {| A := 0, B := 2 |}, {| A := 1, B := 3 |} ]
```

---

## Extend / Project

```slang
table = TableInit( [
    [ "A",  "B",  "C" ],
    [ 1,    2,    3   ],
    [ 4,    5,    6   ],
    [ 7,    8,    9   ],
] );

// Extend: add a computed column
@Structure::Extend( table, \row -> row.A * 2 + row.B, "D" );
// Adds column D with values [ 4, 13, 22 ]

// Project: keep only specified columns
@Structure::Project( table, [ "A", "B" ] );
// Each row has only A and B columns

// Project AllBut: remove specified columns
@Structure::Project( table, [ "C" ], AllBut := True );
// Each row has A and B (C removed)
```

---

## Nested Conversions

### StructOfStructToArrayOfStruct

```slang
S = {| a := {| Apple := "fruit" |}, b := {| Berry := "Drupe" |} |};
@Structure::StructOfStructToArrayOfStruct( S, "Label" );
// [ {| Label := "a", Apple := "fruit" |}, {| Label := "b", Berry := "Drupe" |} ]
```

### ArrayOfStructToStructNested

```slang
Rows = TableInit( [
    [ "Col 1", "Col 2", "Val" ],
    [ "Foo",   "Bar",   "X"   ],
    [ "Foo",   "Tim",   "Y"   ],
    [ "Tim",   "Bar",   "X"   ],
] );

@Structure::ArrayOfStructToStructNested( Rows, [ "Col 1", "Col 2" ] );
// {|
//    Foo := {| Bar := {| Val := "X" |}, Tim := {| Val := "Y" |} |},
//    Tim := {| Bar := {| Val := "X" |} |}
// |}
```

---

## String Formatting

```slang
// Sprintf with structure placeholders
@Structure::Sprintf( "%<Book>:%<Group>", {| Book := 101, Group := "IRP Inflation" |} );
// "101:IRP Inflation"

@Structure::Sprintf( "%<Book>:%<Group>", {| Book := 101, Group := "IRP Inflation" |},
                     Space Replacement Char := "_" );
// "101:IRP_Inflation"

// One Liner
@Structure::One Liner( {| a := 100, b := "Hello" |} );
// "a = 100 , b = Hello"

@Structure::One Liner( {| a := 100, b := "Hello" |}, " | ", ": " );
// "a: 100 | b: Hello"

// Summarise Strings
@Structure::Summarise Strings( {| "Pear" := "yum", "Peach" := "rum" |} );
// "Peach=rum, +1"

@Structure::Summarise Strings( {| "Apple" := "nice" |} );
// "Apple=nice"
```

---

## Bucket / Sample

```slang
// Bucket: distribute keys round-robin into N buckets
S = {| a := 1, b := 2, c := 3, d := 4, e := 5 |};
@Structure::Bucket( S, 3 );
// [ {| a := 1, d := 4 |}, {| b := 2, e := 5 |}, {| c := 3 |} ]

// Sample: keep at most N elements
S = {| a := 1, b := 2, c := 3, d := 4, e := 5 |};
@Structure::Sample( S, 2 );
// An arbitrary 2-element subset, e.g. {| a := 1, b := 2 |}
```

---

## Deep Iteration

```slang
// Iterate Deep: visit every leaf with its path
S = {| A := {| B := 1, C := 2 |}, D := 3 |};
@Structure::Iterate Deep( S, Func( Path, Value ) {
    Printf( "Path: %s, Value: %s\n", StrJoin( ".", Path ), Value );
});
// Prints:
// Path: A.B, Value: 1
// Path: A.C, Value: 2
// Path: D, Value: 3

// KeyValApply InPlace: remove entries matching a condition
S = {| A := 0, B := 5, C := {| D := 0, E := 3 |} |};
@Structure::KeyValApply InPlace( &S,
    Func( Key, &Value ) Value == 0,
);
// S == {| B := 5, C := {| D := 0, E := 3 |} |}
// (only top-level zeros removed; to recurse add Apply To Structures := True)
```

---

## Interpolate

```slang
// Linear interpolation in a 1D structure tree
Data = {| "0" := 0, "10" := 100 |};
@Structure::Interpolate( Data, [ 5 ], [ "Double" ] );
// 50 (linear interpolation halfway between 0 and 100)

// Match mode: exact key lookup
Data = {| "USD" := {| "1Y" := 0.05, "2Y" := 0.06 |} |};
@Structure::Interpolate( Data, [ "USD", "1Y" ], [ "String", "String" ] );
// 0.05
```
