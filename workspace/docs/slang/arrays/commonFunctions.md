# Array Functions -- Quick Reference

A concise lookup of array functions in Slang. For detailed examples see `workingWithArrays.md` and `examples.md`.

This file covers two categories:

1. **Library Functions** (`_LIB Array Functions`) -- require `Link( "_LIB Array Functions" )` and are called with the `@Array::` prefix. These are the most commonly used array utilities.
2. **Built-in Functions** -- available in any script, no `Link()` required.

---

# Part 1: Library Functions (`_LIB Array Functions`)

To use any function in this section, your script must include:

```slang
Link( "_LIB Array Functions" );
```

All functions are called with the `@Array::` prefix, e.g. `@Array::Sort( MyArr )`.

---

## Sorting and Ordering

---

### Array::Sort

**Returns a sorted copy of the array (can be used as RValue). Use the built-in `Sort()` if you don't need an RValue.**

```
/****************************************************************
** Routine: Array::Sort
****************************************************************/
Array::Sort = Func(
    Array( Array ),
    Slang( Ordering ) := Slang(),
)
Returns( Array() )
```

- `Array` -- the array to sort.
- `Ordering` -- (named, optional) custom comparator lambda. Defaults to ascending `<=>`.

```slang
Sorted = @Array::Sort( [ 3, 1, 4, 1, 5 ] );
// [ 1, 1, 3, 4, 5 ]

// Custom ordering: sort strings by length
@Array::Sort( [ "banana", "apple", "plum" ], Ordering := \x,y -> Size( x ) <=> Size( y ) );
// [ "plum", "apple", "banana" ]
```

---

### Array::Sort With Pivot

**Sorts an array in place and returns a pivot array that can restore the original order.**

```
/****************************************************************
** Routine: Array::Sort With Pivot
****************************************************************/
Array::Sort With Pivot = Func(
    Array( &arr ),
    Slang( Ordering ) := \x,y -> x <=> y,
)
Returns( Array() )
```

- `&arr` -- passed by reference; sorted in place.
- `Ordering` -- (named, optional) comparator. Defaults to ascending.

Returns the pivot indices so `Mapcar( \i -> arr[i], pivot )` restores the original order.

```slang
A = [ 23, 11, 42, 1 ];
Pivot = @Array::Sort With Pivot( &A );
// A is now [ 1, 11, 23, 42 ]
// Mapcar( \i -> A[i], Pivot ) restores original order
```

---

### Array::SortTable

**Calls `SortTable` and returns a copy (RValue).**

```
/****************************************************************
** Routine: Array::SortTable
****************************************************************/
Array::SortTable = Func(
    Array( Array ),
    Array( Ordering ) = [],
)
Returns( Array() )
```

- `Array` -- array of structures to sort.
- `Ordering` -- array of key names to sort by.

```slang
Sorted = @Array::SortTable( Data, [ "Name", "Age" ] );
```

---

### Array::Sort Indices

**Returns an array of indices that would sort the original array.**

```
/****************************************************************
** Routine: Array::Sort Indices
****************************************************************/
Array::Sort Indices = Func(
    Array( RefArr ),
    Slang( Sort Func ) := Slang(),
)
Returns( Array() )
```

- `RefArr` -- the reference array.
- `Sort Func` -- (named, optional) custom comparator.

```slang
Idx = @Array::Sort Indices( [ 30, 10, 20 ] );
// Idx = [ 1, 2, 0 ] -- i.e. element at index 1 is smallest
```

---

### Array::SortByIndex

**Calls `SortByIndex` and returns a copy (RValue).**

```
/****************************************************************
** Routine: Array::SortByIndex
****************************************************************/
Array::SortByIndex = Func(
    Array( Array ),
    Double( Index ),
)
Returns( Array() )
```

- `Index` -- the sub-array index to sort by.

---

### Array::Order Fn

**Returns a comparator function for sorting an array according to a prescribed element order.**

```
/****************************************************************
** Routine: Array::Order Fn
****************************************************************/
Array::Order Fn = Func(
    Array( List ),
    Double( New At Front ) := True,
)
Returns( Slang() )
```

- `List` -- the desired ordering of elements.
- `New At Front` -- (named, optional) if True (default), elements not in `List` sort to the front; if False, to the back.

```slang
Cmp = @Array::Order Fn( [ "High", "Medium", "Low" ] );
Sort( MyArr, Cmp );
// MyArr is now ordered: High, Medium, Low (unknowns at front by default)
```

---

### Array::Array Cmp For Sort

**Comparator for sorting a table (array of arrays) by multiple columns, with optional per-column transforms.**

```
/****************************************************************
** Routine: Array::Array Cmp For Sort
****************************************************************/
Array::Array Cmp For Sort = Func(
    a,
    b,
    Array( Idxs ) = [ 0 ],
    Array( Ops ) = [],
    Ref Date = Pricing Date( "Security Database" ),
)
Returns( Double() )
```

- `Idxs` -- column indices to sort by. Negative = descending.
- `Ops` -- per-column transform: `"Abs"`, `"Date"`, `"RDate"`, `"DateR"`, or `""`.

```slang
// Sort table by absolute value of column 2 (descending), then column 1 (ascending)
Sort( Tab, \a,b -> @Array::Array Cmp For Sort( a, b, [ -2, 1 ], [ "Abs" ] ) );
```

---

### Array::Is Sorted

**Checks if an array is in strictly ascending order. Returns True or an error describing the violation.**

```
/****************************************************************
** Routine: Array::Is Sorted
****************************************************************/
Array::Is Sorted = Func(
    Array( Arr ),
    Double( Allow Duplicates ) := False,
    Slang( Comparator ) := Slang(),
)
Returns( Double() )
```

- `Allow Duplicates` -- (named, optional) if True, `>=` comparison is used instead of `>`.
- `Comparator` -- (named, optional) custom comparator function.

```slang
@Array::Is Sorted( [ 1, 2, 3, 4 ] );                         // True
@Array::Is Sorted( [ 1, 2, 2, 3 ] );                         // Err(...)
@Array::Is Sorted( [ 1, 2, 2, 3 ], Allow Duplicates := True ); // True
```

---

### Array::Rank

**Returns an array giving the rank of each element (descending rank by default).**

```
/****************************************************************
** Routine: Array::Rank
****************************************************************/
Array::Rank = Func(
    Array( RefArr ),
    Double( Base ) := 0,
)
Returns( Array() )
```

- `Base` -- (named, optional) starting rank value. Default 0.

```slang
@Array::Rank( [ 100, 11, -4, 11, 9, 11 ] );
// [ 0, 1, 5, 1, 4, 1 ]
```

---

### Array::Rank With Possible Duplicates

**Like `Array::Rank` but with control over duplicate treatment (Min, Max, or Avg).**

```
/****************************************************************
** Routine: Array::Rank With Possible Duplicates
****************************************************************/
Array::Rank With Possible Duplicates = Func(
    Array( RefArr ),
    Double( Base ) := 0,
    Double( Dups_Avg ) := 0,
    Double( Dups_Max ) := 0,
)
Returns( Array() )
```

- `Dups_Avg` -- (named, optional) use average rank for duplicates.
- `Dups_Max` -- (named, optional) use max rank for duplicates.

---

## Searching and Lookup

---

### Array::FindByValue

**Searches an array for a value. Returns the index, or -1 if not found.**

```
/****************************************************************
** Routine: Array::FindByValue
****************************************************************/
Array::FindByValue = Func(
    Array( &A ),
    Any( Value ),
    EqualFunc = Null,
    Double( First ) := True,
)
Returns( Double() )
```

- `&A` -- array to search (by reference for speed).
- `Value` -- value to find.
- `EqualFunc` -- (positional, optional) custom two-arg equality function. Default: `==`.
- `First` -- (named, optional) if True (default), return index of first match; if False, last match.

```slang
A = [ 1, 2, 3, 4, 5 ];
@Array::FindByValue( &A, 3 );                // 2
@Array::FindByValue( &A, 6 );                // -1

// With custom equality on array of structures
B = [ {| a := 1 |}, {| a := 2 |}, {| a := 3 |} ];
@Array::FindByValue( &B, 3, Func( Elem, Val ) { Return( Elem.a == Val ); } ); // 2
```

---

### Array::FindIndexOfNearestValue

**Returns the index of the element closest to a given value.**

```
/****************************************************************
** Routine: Array::FindIndexOfNearestValue
****************************************************************/
Array::FindIndexOfNearestValue = Func(
    Array( A ),
    Any( Value ),
    Double( Unsorted ) := False,
)
Returns( Double() )
```

- `A` -- array of comparable values.
- `Value` -- value to find nearest to.
- `Unsorted` -- (named, optional) set True if array is not sorted. Default False (binary search on sorted array).

```slang
@Array::FindIndexOfNearestValue( [ 0, 1 ], 2 );                                    // 1
@Array::FindIndexOfNearestValue( [ 3, -4, 5, 6, 2, 1 ], 2.1, Unsorted := True );  // 4
```

---

### Array::Contains

**Return True if array contains a value. Optionally outputs the index.**

```
/****************************************************************
** Routine: Array::Contains
****************************************************************/
Array::Contains = Func(
    SubscriptableDatatype( ArrayOrSlice ),
    Any( Value Or Predicate ),
    Double( Binary Search ) := False,
    Double( &Index ) := -1,
)
Returns( Double() )
```

- `Value Or Predicate` -- a value to find, or a predicate lambda.
- `Binary Search` -- (named, optional) use binary search (array must be sorted).
- `&Index` -- (named, optional, by reference) receives the index of the found element (-1 if not found).

```slang
@Array::Contains( [ 1, 2, 3 ], 2 );                     // True
@Array::Contains( [ 1, 2, 3 ], 5 );                     // False

Idx = -1;
@Array::Contains( [ 10, 20, 30 ], 20, Index := Idx );   // True, Idx == 1
```

---

### Array::Contains Multiple Items

**Checks if an array contains some (or all) items from another array. Both arrays should be sorted and unique.**

```
/****************************************************************
** Routine: Array::Contains Multiple Items
****************************************************************/
Array::Contains Multiple Items = Func(
    Array( ArrayToSearch ),
    Array( ItemsToSearchFor ),
    Double( All ) := False,
)
Returns( Double() )
```

- `All` -- (named, optional) if True, ALL items must be found. Default False (any match suffices).

```slang
@Array::Contains Multiple Items( [ 1, 2, 3 ], [ 1, 4 ], All := False ); // True
@Array::Contains Multiple Items( [ 1, 2, 3 ], [ 1, 4 ], All := True );  // False
@Array::Contains Multiple Items( [ 1, 2, 3 ], [ 1, 2 ], All := True );  // True
```

---

### Array::Contains Array

**Like `Contains Multiple Items`, but with an option to auto-sort/unique the inputs.**

```
/****************************************************************
** Routine: Array::Contains Array
****************************************************************/
Array::Contains Array = Func(
    Array( ArrayToSearch ),
    Array( ItemsToSearchFor ),
    Double( All ) := False,
    Double( IsSortedNUnique ) := True,
)
Returns( Double() )
```

- `IsSortedNUnique` -- (named, optional) set False if inputs are not already sorted and unique.

---

### Array::Binary Search First

**Binary search for the first index where a predicate becomes True. The predicate must be non-decreasing across the array.**

```
/****************************************************************
** Routine: Array::Binary Search First
****************************************************************/
Array::Binary Search First = Func(
    Array( Array ),
    Slang( Predicate ),
)
Returns( Double(), Null )
```

Returns the index, or Null if predicate is never True.

```slang
@Array::Binary Search First( [ 1, 1, 1, 4, 4 ], \x -> Mod( x, 2 ) == 0 );
// 3
```

---

### Array::Binary Search Last

**Like `Binary Search First`, but for the last index where predicate is True (predicate must be non-increasing after that point).**

```
/****************************************************************
** Routine: Array::Binary Search Last
****************************************************************/
Array::Binary Search Last = Func(
    Array( Array ),
    Slang( Predicate ),
)
Returns( Double(), Null )
```

---

### Array::LowerBound

**Binary search returning the first position where a value can be inserted without violating sort order.**

```
/****************************************************************
** Routine: Array::LowerBound
****************************************************************/
Array::LowerBound = Func(
    Array( a ),
    Any( b ),
    Slang( less ) = Func( x, y ) Returns( Double() ) Return( x < y ),
)
Returns( Double() )
```

- `less` -- (positional, optional) custom "less than" comparator.

```slang
@Array::LowerBound( [ 1, 2, 3, 4 ], 3 );   // 2
@Array::LowerBound( [ 1, 2, 3, 4 ], 1.5 );  // 1
```

---

### Array::UpperBound

**Binary search returning the last position where a value can be inserted without violating sort order.**

```
/****************************************************************
** Routine: Array::UpperBound
****************************************************************/
Array::UpperBound = Func(
    Array( a ),
    Any( b ),
    Slang( less ) = Func( x, y ) Returns( Double() ) Return( x < y ),
)
Returns( Double() )
```

```slang
@Array::UpperBound( [ 1, 1, 3, 4 ], 1 );  // 2
@Array::UpperBound( [ 1, 2, 3, 4 ], 3 );  // 3
```

---

### Array::Find SubArray

**Find where a subarray exists inside another array. Returns 0-based index or -1.**

```
/****************************************************************
** Routine: Array::Find SubArray
****************************************************************/
Array::Find SubArray = Func(
    Array( To Search ),
    Array( SubArray ),
    Double( Start ) = 0,
)
Returns( Double() )
```

- `Start` -- (positional, optional) position to begin search. Default 0.

```slang
@Array::Find SubArray( [ "A", "B", "C", "D", "E" ], [ "C", "D" ] );  // 2
@Array::Find SubArray( [ "A", "B", "C" ], [ "D", "C" ] );            // -1
```

---

### Array::Find Nearest

**Finds the index (and/or value) of the nearest element in an array to a given value.**

```
/****************************************************************
** Routine: Array::Find Nearest
****************************************************************/
Array::Find Nearest = Func(
    Array( Array ),
    Any( Value ),
    Double( Is Sorted ) := True,
    Double( Return Value ) := False,
    Double( Return Both ) := False,
    Slang( Distance Func ) := Func( a, b ) Abs( a - b ),
)
Returns( Any() )
```

- `Is Sorted` -- (named, optional) set False for unsorted arrays (uses linear scan).
- `Return Value` -- (named, optional) return the value instead of the index.
- `Return Both` -- (named, optional) return `[ index, value ]`.
- `Distance Func` -- (named, optional) custom distance function.

```slang
@Array::Find Nearest( [ 10, 20, 30, 40 ], 27 );                      // 2 (index of 30)
@Array::Find Nearest( [ 10, 20, 30, 40 ], 27, Return Value := True ); // 30
```

---

### Array::Match String

**Find the best fuzzy match for a string in an array of candidates (using convolution scoring).**

```
/****************************************************************
** Routine: Array::Match String
****************************************************************/
Array::Match String = Func(
    Array( Candidates ),
    String( Target ),
    String( Method ) := "Convolution",
)
Returns( String(), Error() )
```

---

## Set Operations (Intersection, Diff, Union)

---

### Array::Intersection

**Intersection of two sorted arrays. Returns elements common to both.**

```
/****************************************************************
** Routine: Array::Intersection
****************************************************************/
Array::Intersection = Func(
    Array( Array1 ),
    Array( Array2 ),
    Double( Sort ) := False,
    Slang( Compare Func ) := Slang(),
)
Returns( Array() )
```

- `Sort` -- (named, optional) sort the arrays first.
- `Compare Func` -- (named, optional) custom comparator.

> **Important:** Arrays must already be sorted in ascending order unless `Sort := True`.

```slang
@Array::Intersection( [ 1, 2, 7, 23 ], [ 2, 7, 23 ] );             // [ 2, 7, 23 ]
@Array::Intersection( [ 5, 1, 3 ], [ 3, 1, 7 ], Sort := True );     // [ 1, 3 ]
```

---

### Array::Intersection Stable

**Intersection preserving the order of the first array. Does NOT require sorted inputs.**

```
/****************************************************************
** Routine: Array::Intersection Stable
****************************************************************/
Array::Intersection Stable = Func(
    Array( Array1 ),
    Array( Array2 ),
    Slang( Compare Func ) := Slang(),
    Double( Can Swap Arg Order ) := False,
)
Returns( Array() )
```

- `Can Swap Arg Order` -- (named, optional) if True, internally swaps args for optimal performance; output order follows the larger array.

```slang
@Array::Intersection Stable( [ 1, 832, 2, 43, 23 ], [ 23, 832 ] );
// [ 832, 23 ] -- preserves order of first array
```

---

### Array::Intersection Many

**Intersection of an arbitrary number of sorted arrays.**

```
/****************************************************************
** Routine: Array::Intersection Many
****************************************************************/
Array::Intersection Many = Func(
    Array( Arrays ),
    Double( Sort ) := False,
    Slang( Compare Func ) := Slang(),
)
Returns( Array() )
```

- `Arrays` -- array of arrays to intersect.

```slang
@Array::Intersection Many( [ [ 1, 3, 5, 6 ], [ 3, 6, 9 ], [ 2, 4, 6, 9 ] ] );
// [ 6 ] (if already sorted) -- but safer: use Sort := True
```

---

### Array::Diff

**Elements in A1 not contained in A2 (relative complement). Optionally sorts the result.**

```
/****************************************************************
** Routine: Array::Diff
****************************************************************/
Array::Diff = Func(
    Array( A1 ),
    Array( A2 ),
    Double( Sort Result ) = True,
    Slang( Sort Fn ) = Slang(),
)
Returns( Array() )
```

- `Sort Result` -- (positional, optional) sort the output. Default True.
- `Sort Fn` -- (positional, optional) custom sort function for result.

```slang
@Array::Diff( [ 1, 3, 7, 5, 9, 5, 7 ], [ 25, 16, 9, 4, 1, 16 ], True );
// [ 3, 5, 5, 7, 7 ]
```

---

### Array::DiffUnique

**Like `Array::Diff`, but returns only unique elements.**

```
/****************************************************************
** Routine: Array::DiffUnique
****************************************************************/
Array::DiffUnique = Func(
    Array( A1 ),
    Array( A2 ),
    Double( Sort Result ) = True,
)
Returns( Array() )
```

---

### Array::DiffUnique Case Sensitive

**Like `DiffUnique`, but treats strings with different case as different elements.**

```
/****************************************************************
** Routine: Array::DiffUnique Case Sensitive
****************************************************************/
Array::DiffUnique Case Sensitive = Func(
    Array( A1 ),
    Array( A2 ),
    Double( Sort Result ) = True,
)
Returns( Array() )
```

---

### Array::Diff All

**Swiss-army-knife set operation: diffs, intersection, union, duplicate detection, case sensitivity, and unique/sort outputs -- all in one call.**

```
/****************************************************************
** Routine: Array::Diff All
****************************************************************/
Array::Diff All = Func(
    Array( Left ),
    Array( Right ),
    Double( Case Sensitive ) := False,
    Double( Do Intersection ) := False,
    Double( Do Union ) := False,
    Double( Find Dupes ) := False,
    Double( Sort Outputs ) := False,
    Double( Unique Outputs ) := False,
)
Returns( Structure() )
```

Always returns `{| Left Only := [...], Right Only := [...] |}`. Additional components appear when requested.

- `Case Sensitive` -- (named, optional) case-sensitive string comparison.
- `Do Intersection` -- (named, optional) include `Intersection` component.
- `Do Union` -- (named, optional) include `Union` component.
- `Find Dupes` -- (named, optional) include `Left Dupes` and `Right Dupes`.
- `Sort Outputs` -- (named, optional) sort each output list.
- `Unique Outputs` -- (named, optional) deduplicate `Left Only` and `Right Only`.

```slang
R = @Array::Diff All( [ 1, 3, 7, 5 ], [ 25, 9, 1 ], Do Intersection := True, Sort Outputs := True );
// R.Left Only    = [ 3, 5, 7 ]
// R.Right Only   = [ 9, 25 ]
// R.Intersection = [ 1 ]
```

---

### Array::Classify Sets

**Given two arrays, compute A Intersect B, A Minus B, and B Minus A. Faster than `Diff All` when inputs are already sorted.**

```
/****************************************************************
** Routine: Array::Classify Sets
****************************************************************/
Array::Classify Sets = Func(
    Array( ArrayA ),
    Array( ArrayB ),
    Compare Pred = Null,
    Double( SortItFirst ) := True,
    String( Label A ) := "A",
    String( Label B ) := "B",
)
Returns( Structure() )
```

- `Compare Pred` -- (positional, optional) custom 3-way comparator e.g. `\X, Y -> X.field <=> Y.field`.
- `SortItFirst` -- (named, optional) set False if arrays are already sorted.
- `Label A`, `Label B` -- (named, optional) custom labels for result keys (e.g. `"Alpha Intersect Beta"`).

```slang
R = @Array::Classify Sets( [ 1, 3, 5 ], [ 2, 3, 4 ] );
// R.A Intersect B = [ 3 ]
// R.A Minus B     = [ 1, 5 ]
// R.B Minus A     = [ 2, 4 ]
```

---

### Array::Union

**Union of an arbitrary number of arrays (sorted and uniqued).**

```
/****************************************************************
** Routine: Array::Union
****************************************************************/
Array::Union = Func(
    Ellipsis( Arrays ) = [],
)
Returns( Array() )
```

```slang
@Array::Union( [ 3, 1, 2 ], [ 2, 4, 5 ], [ 1, 6 ] );
// [ 1, 2, 3, 4, 5, 6 ]
```

---

### Array::Union No Sort

**Concatenate arrays keeping only unique entries, preserving original order.**

```
/****************************************************************
** Routine: Array::Union No Sort
****************************************************************/
Array::Union No Sort = Func(
    Ellipsis( Arrays ) = [],
)
Returns( Array() )
```

```slang
@Array::Union No Sort( [ 3, 1, 2 ], [ 2, 4 ] );
// [ 3, 1, 2, 4 ]
```

---

### Array::Union With Compare Func

**Union of two sorted arrays with a custom comparator. First array's elements take precedence.**

```
/****************************************************************
** Routine: Array::Union With Compare Func
****************************************************************/
Array::Union With Compare Func = Func(
    Array( Array1 ),
    Array( Array2 ),
    Double( Sort ) := False,
    Slang( Compare Func ) := Slang(),
)
Returns( Array() )
```

---

### Array::Exclusion

**Symmetric difference (XOR): elements in A or B but not in both.**

```
/****************************************************************
** Routine: Array::Exclusion
****************************************************************/
Array::Exclusion = Func(
    Array( A ),
    Array( B ),
)
Returns( Array() )
```

---

### Array::Disjoint

**Returns True if two arrays share no common elements.**

```
/****************************************************************
** Routine: Array::Disjoint
****************************************************************/
Array::Disjoint = Func(
    Array( Array1 ),
    Array( Array2 ),
)
Returns( Double() )
```

```slang
@Array::Disjoint( [ 1, 2 ], [ 3, 4 ] );  // True
@Array::Disjoint( [ 1, 2 ], [ 2, 3 ] );  // False
```

---

## Uniqueness and Duplicates

---

### Array::Unique

**Returns a sorted, deduplicated copy of the array (RValue). Wraps built-in `ArrayUnique`.**

```
/****************************************************************
** Routine: Array::Unique
****************************************************************/
Array::Unique = Func(
    Array( Array ),
    Slang( Ordering ) := Slang(),
    Double( Already Sorted ) := False,
)
Returns( Array() )
```

- `Ordering` -- (named, optional) custom comparator for sort + unique.
- `Already Sorted` -- (named, optional) skip sorting if True.

```slang
@Array::Unique( [ 3, 1, 2, 1, 3 ] );
// [ 1, 2, 3 ]
```

---

### Array::Unique Stable

**Deduplicate preserving insertion order (keeps first occurrence).**

```
/****************************************************************
** Routine: Array::Unique Stable
****************************************************************/
Array::Unique Stable = Func(
    Array( Array ),
)
Returns( Array() )
```

```slang
@Array::Unique Stable( [ 5, 2, 4, 5, 2, 3 ] );
// [ 5, 2, 4, 3 ]
```

---

### Array::Duplicates

**Returns an array of elements that appear more than once.**

```
/****************************************************************
** Routine: Array::Duplicates
****************************************************************/
Array::Duplicates = Func(
    Array( A ),
    Double( Case Sensitive Strings ) := False,
)
Returns( Array() )
```

- `Case Sensitive Strings` -- (named, optional) if True, `"A"` and `"a"` are considered different. Array must then contain only strings.

---

### Array::Is Unique

**Returns True if all elements are unique.**

```
/****************************************************************
** Routine: Array::Is Unique
****************************************************************/
Array::Is Unique = Func(
    Array( A ),
    Double( Case Sensitive Strings ) := False,
)
Returns( Double() )
```

---

### Array::NonUnique Elements

**Returns elements that appear more than once (each listed once).**

```
/****************************************************************
** Routine: Array::NonUnique Elements
****************************************************************/
Array::NonUnique Elements = Func(
    Array( Array ),
    Double( Already Sorted ) := False,
    Slang( Ordering ) := Slang(),
)
Returns( Array() )
```

---

### Array::CountDistinct

**Number of distinct elements in an array.**

```
/****************************************************************
** Routine: Array::CountDistinct
****************************************************************/
Array::CountDistinct = Func(
    Array( List ),
)
Returns( Double() )
```

```slang
@Array::CountDistinct( [ 1, 1, 2, 2, 3, 3, 4, 4 ] );  // 4
```

---

### Array::Has Identical Elements

**Returns True if all elements are equal (optionally to a specific value).**

```
/****************************************************************
** Routine: Array::Has Identical Elements
****************************************************************/
Array::Has Identical Elements = Func(
    Array( Array ),
    Any( Equal To ) := If( Size( Array ) ) Array[ 0 ] : Null,
)
Returns( Double() )
```

- `Equal To` -- (named, optional) compare all elements to this value.

```slang
@Array::Has Identical Elements( [ 1, 1, 1, 1 ] );                  // True
@Array::Has Identical Elements( [ 1, 1, 1, 2 ] );                  // False
@Array::Has Identical Elements( [ 1, 1, 1, 1 ], Equal To := 2 );   // False
```

---

### Array::Remove Duplicates

**Remove duplicates from an array in place. Array must be sorted (or pass `SortIt := True`).**

```
/****************************************************************
** Routine: Array::Remove Duplicates
****************************************************************/
Array::Remove Duplicates = Func(
    Array( &Arr ),
    Slang( Compare ) = Func( A, B ) { Return( A <=> B ); },
    Double( SortIt ) := False,
)
Returns( Double() )
```

- `&Arr` -- modified in place.
- `Compare` -- (positional, optional) custom comparator.
- `SortIt` -- (named, optional) sort before dedup.

```slang
A = [ 3, 1, 4, 3, 3 ];
@Array::Remove Duplicates( &A, SortIt := True );
// A is now [ 1, 3, 4 ]
```

---

## Filtering and Selection

---

### Array::Grep

**Filter array by a predicate lambda. Returns elements where the filter is True.**

```
/****************************************************************
** Routine: Array::Grep
****************************************************************/
Array::Grep = Func(
    Any( Input ),
    Slang( Filter ) = Func( x ) x,
)
Returns( Any() )
```

```slang
@Array::Grep( [ 1, 2, 3, 4, 5 ], \x -> x > 3 );
// [ 4, 5 ]
```

---

### Array::Grep Indices

**Return indices of elements where a filter is True.**

```
/****************************************************************
** Routine: Array::Grep Indices
****************************************************************/
Array::Grep Indices = Func(
    SubscriptableDatatype( Array ),
    Slang( Filter ) = Func( x ) x,
)
Returns( Array() )
```

```slang
@Array::Grep Indices( [ 10, 20, 30, 40 ], \x -> x >= 25 );
// [ 2, 3 ]
```

---

### Array::Grep Indices Slice

**Like `Grep Indices` but uses a type-slice internally. Prefer this unless your filter has nested lambda capture issues.**

```
/****************************************************************
** Routine: Array::Grep Indices Slice
****************************************************************/
Array::Grep Indices Slice = Func(
    SubscriptableDatatype( Array ),
    Slang( Filter ) = Func( x ) x,
)
Returns( Array() )
```

---

### Array::Grep Type

**Return elements of a specific data type (via `TypeOf()`).**

```
/****************************************************************
** Routine: Array::Grep Type
****************************************************************/
Array::Grep Type = Func(
    Any( Input ),
    String( Type ),
)
Returns( Array() )
```

```slang
@Array::Grep Type( [ 1, "hello", 3.14, "world" ], "String" );
// [ "hello", "world" ]
```

---

### Array::Select

**Select elements by a True/False mask array.**

```
/****************************************************************
** Routine: Array::Select
****************************************************************/
Array::Select = Func(
    Array( A ),
    SubscriptValueVector( Mask ),
)
Returns( Array() )
```

- `Mask` -- boolean array/vector of same size as A.

```slang
@Array::Select( [ "a", "b", "c", "d" ], [ True, False, True, False ] );
// [ "a", "c" ]
```

---

### Array::Filter Errors By Type

**Returns a copy of the array keeping non-error elements and error elements of a specific data type.**

```
/****************************************************************
** Routine: Array::Filter Errors By Type
****************************************************************/
Array::Filter Errors By Type = Func(
    Array( List ),
    String( Filter ),
)
Returns( Array() )
```

---

### Array::DeleteByValue

**Removes all occurrences of a value from an array.**

```
/****************************************************************
** Routine: Array::DeleteByValue
****************************************************************/
Array::DeleteByValue = Func(
    Array( &A ),
    Value,
    EqualFunc = Null,
    Double( In Place ) := False,
)
Returns( Double() )
```

- `&A` -- modified in place.
- `EqualFunc` -- (positional, optional) custom equality function.
- `In Place` -- (named, optional) True for slower but more memory-efficient in-place removal.

Returns True if any element was deleted.

---

### Array::DeleteByProperty

**Delete all elements matching a predicate lambda.**

```
/****************************************************************
** Routine: Array::DeleteByProperty
****************************************************************/
Array::DeleteByProperty = Func(
    Array( &Array ),
    Any( Property ),
)
Returns()
```

- `Property` -- a lambda or string function name. Elements where it returns True are removed.

```slang
A = [ 1, 2, 3, 4, 5, 6 ];
@Array::DeleteByProperty( &A, \x -> Mod( x, 2 ) == 0 );
// A is now [ 1, 3, 5 ]
```

---

### Array::DelArrayVal

**Returns a copy of the array with all occurrences of a value removed.**

```
/****************************************************************
** Routine: Array::DelArrayVal
****************************************************************/
Array::DelArrayVal = Func(
    Array( a ),
    Any( Val ),
)
Returns( Array() )
```

```slang
@Array::DelArrayVal( [ "foo", "bar", "baz" ], "bar" );
// [ "foo", "baz" ]
```

---

### Array::First

**Find the first element matching a predicate. Throws if not found (or returns a default).**

```
/****************************************************************
** Routine: Array::First
****************************************************************/
Array::First = Func(
    Array( Sequence ),
    Slang( Pred ) = \x -> x == x,
    Any( Default ) := Error Value,
    Double( Throw ) := True,
)
Returns( Any() )
```

- `Pred` -- (positional, optional) predicate lambda.
- `Default` -- (named, optional) value to return if not found (only used when `Throw := False`).
- `Throw` -- (named, optional) if False, return `Default` instead of throwing.

```slang
@Array::First( [ "a", "z", "y" ], \n -> n != "a" );  // "z"
```

---

### Array::Take While

**Returns the longest prefix of elements satisfying a predicate.**

```
/****************************************************************
** Routine: Array::Take While
****************************************************************/
Array::Take While = Func(
    Array( Array ),
    Slang( Predicate ),
)
Returns( Array() )
```

```slang
@Array::Take While( [ 1, 2, 3, 4 ], \x -> x < 4 );
// [ 1, 2, 3 ]
```

---

### Array::Get Only Element

**Assert that array has exactly one element and return it.**

```
/****************************************************************
** Routine: Array::Get Only Element
****************************************************************/
Array::Get Only Element = Func(
    Array( Array ),
    String( Error Message ) = "expected array of size 1 to extract only element",
)
Returns( Any() )
```

---

### Array::Get Only Element Where

**Assert that exactly one element matches a predicate and return it.**

```
/****************************************************************
** Routine: Array::Get Only Element Where
****************************************************************/
Array::Get Only Element Where = Func(
    Array( Array ),
    Slang( Filter ),
)
Returns( Any() )
```

---

### Array::Get Unique Element

**If all elements are identical, return that element. Otherwise throw.**

```
/****************************************************************
** Routine: Array::Get Unique Element
****************************************************************/
Array::Get Unique Element = Func(
    Array( Array ),
)
Returns( Any() )
```

---

## Extraction and Slicing

---

### Array::Tail

**Returns array without the first element. Throws on empty array.**

```
/****************************************************************
** Routine: Array::Tail
****************************************************************/
Array::Tail = Func(
    Array( Array ),
)
Returns( Array() )
```

```slang
@Array::Tail( [ 1, 2, 3 ] );  // [ 2, 3 ]
@Array::Tail( [ 1 ] );        // []
```

---

### Array::Last

**Returns the last element (or Nth-to-last). Wraps built-in `Back()`.**

```
/****************************************************************
** Routine: Array::Last
****************************************************************/
Array::Last = Func(
    Array( A ),
    Double( Offset ) = 0,
)
Returns( Any() )
```

- `Offset` -- (positional, optional) 0 = last, 1 = second-to-last, etc.

```slang
@Array::Last( [ 10, 20, 30 ] );     // 30
@Array::Last( [ 10, 20, 30 ], 1 );  // 20
```

---

### Array::Extract Strict

**Extract elements with strict bounds checking. Throws on out-of-bounds.**

```
/****************************************************************
** Routine: Array::Extract Strict
****************************************************************/
Array::Extract Strict = Func(
    Array( Array ),
    Double( Index ),
    Double( Count ) = Size( Array ) - Index,
)
Returns( Array() )
```

- `Index` -- starting index (0-based).
- `Count` -- (positional, optional) number of elements. Default: all remaining from Index.

```slang
@Array::Extract Strict( [ "a", "b", "c", "d" ], 1, 2 );
// [ "b", "c" ]
```

---

### Array::Extract

**Like `ArrayExtract`, but works on all indexable types and clips gracefully at the end.**

```
/****************************************************************
** Routine: Array::Extract
****************************************************************/
Array::Extract = Func(
    SubscriptableDatatype( Input ),
    Double( From ),
    Double( Count ) = Size( Input ) - From,
)
Returns( SubscriptableDatatype() )
```

---

### Array::Extract Selection

**Extract elements at specific indices.**

```
/****************************************************************
** Routine: Array::Extract Selection
****************************************************************/
Array::Extract Selection = Func(
    SubscriptableDatatype( A ),
    Array( Idx ),
)
Returns( Array() )
```

```slang
@Array::Extract Selection( [ "a", "b", "c", "d", "e" ], [ 0, 2, 4 ] );
// [ "a", "c", "e" ]
```

---

### Array::Extract Indices From Sorted

**Returns `[ start, length ]` of a sub-sequence within a sorted array between low/high limits.**

```
/****************************************************************
** Routine: Array::Extract Indices From Sorted
****************************************************************/
Array::Extract Indices From Sorted = Func(
    Array( Array ),
    Any( Low Limit ),
    Any( High Limit ),
    Double( Left Open ) := False,
    Double( Right Open ) := False,
)
Returns( Array() )
```

- `Left Open` -- (named, optional) exclude the low limit value.
- `Right Open` -- (named, optional) exclude the high limit value.

```slang
@Array::Extract Indices From Sorted( [ 1, 2, 3, 4, 5 ], 2, 4 );
// [ 1, 3 ] -- start at index 1, length 3
```

---

### Array::Extract Region

**Extract a rectangular region from a 2D array.**

```
/****************************************************************
** Routine: Array::Extract Region
****************************************************************/
Array::Extract Region = Func(
    Array( A ),
    Double( Row From ),
    Double( Num Rows ),
    Double( Col From ),
    Double( Num Cols ),
)
Returns( Array() )
```

---

## Transformation and Mapping

---

### Array::And

**True if predicate is True for ALL elements. Alias for `Functional::All`. True for empty arrays.**

```
/****************************************************************
** Routine: Array::And
****************************************************************/
Array::And = Func(
    Array( a ),
    Slang( Predicate ) = \x -> x,
)
Returns( Double() )
```

```slang
@Array::And( [ 1, 2, 3, 4 ], \n -> n < 5 );   // True
@Array::And( [ 1, 2, 3, 4 ], \n -> n < 3 );   // False
```

---

### Array::Or

**True if predicate is True for ANY element. Alias for `Functional::Any`.**

```
/****************************************************************
** Routine: Array::Or
****************************************************************/
Array::Or = Func(
    Array( a ),
    Slang( Predicate ) = \x -> x,
)
Returns( Double() )
```

---

### Array::Count

**Count how many elements satisfy a predicate.**

```
/****************************************************************
** Routine: Array::Count
****************************************************************/
Array::Count = Func(
    Any( Arr ),
    Slang( fn ),
)
Returns( Double() )
```

```slang
@Array::Count( [ 1, 2, 3, 4, 5 ], \x -> x > 3 );  // 2
```

---

### Array::Partition

**Split array into two groups based on a predicate. Returns `GStructure( True, [...], False, [...] )`.**

```
/****************************************************************
** Routine: Array::Partition
****************************************************************/
Array::Partition = Func(
    Array( Item Array ),
    Slang( Predicate ),
)
Returns( GStructure() )
```

```slang
@Array::Partition( [ "a", "b" ], \X -> X == "a" );
// GStructure( True, [ "a" ], False, [ "b" ] )
```

---

### Array::Abs

**Returns a copy with absolute values applied to each element.**

```
/****************************************************************
** Routine: Array::Abs
****************************************************************/
Array::Abs = Func(
    Array( A ),
)
Returns( Array() )
```

```slang
@Array::Abs( [ -1, 2, -3, 4 ] );  // [ 1, 2, 3, 4 ]
```

---

### Array::Round

**Returns a copy rounded to the given precision.**

```
/****************************************************************
** Routine: Array::Round
****************************************************************/
Array::Round = Func(
    Array( A ),
    Double( Precision ) = 0,
)
Returns( Array() )
```

---

### Array::Restrict

**Clamp each element between a floor and cap.**

```
/****************************************************************
** Routine: Array::Restrict
****************************************************************/
Array::Restrict = Func(
    Array( A ),
    Double( Floor ) = LowLimit( "Double" ),
    Double( Cap ) = HighLimit( "Double" ),
    Double( Force Floor ) := False,
    Double( Catch Error ) := True,
)
Returns( Array() )
```

---

### Array::To

**Cast all elements to a given type.**

```
/****************************************************************
** Routine: Array::To
****************************************************************/
Array::To = Func(
    Array( Array ),
    String( Type ) = "Double",
)
Returns( Array() )
```

```slang
@Array::To( [ "1", "2.5", "3" ], "Double" );
// [ 1, 2.5, 3 ]
```

---

### Array::Cast Elements To

**Like `Array::To` but recurses into nested arrays.**

```
/****************************************************************
** Routine: Array::Cast Elements To
****************************************************************/
Array::Cast Elements To = Func(
    Array( Arr ),
    String( To Type ),
)
Returns( Array() )
```

```slang
@Array::Cast Elements To( [ "1", [ "2.0" ] ], "Double" );
// [ 1, [ 2 ] ]
```

---

### Array::StrUpperInPlace

**Uppercases all string elements in place.**

```
/****************************************************************
** Routine: Array::StrUpperInPlace
****************************************************************/
Array::StrUpperInPlace = Func(
    Array( &A ),
)
Returns( Double() )
```

---

### Array::Replace Words In Array

**Returns a copy replacing occurrences of a word within string elements.**

```
/****************************************************************
** Routine: Array::Replace Words In Array
****************************************************************/
Array::Replace Words In Array = Func(
    Array( A ),
    String( Word ),
    String( Replace With ),
    Double( Remove All Occurences ) := True,
)
Returns( Array() )
```

- `Remove All Occurences` -- (named, optional) if False, only the first occurrence per element is replaced.

---

### Array::Find And Replace

**Find a value in an array and replace it (returns a copy).**

```
/****************************************************************
** Routine: Array::Find And Replace
****************************************************************/
Array::Find And Replace = Func(
    Array( &X ),
    Target,
    Replace With,
    Double( Replace All Occurrences ) := False,
    Double( Throw If Not Found ) := False,
)
Returns( Array() )
```

---

## Grouping and Classification

---

### Array::Subsets By Classification

**Group array elements by a classifier function into a Structure (or GStructure, StructureCase, etc.).**

```
/****************************************************************
** Routine: Array::Subsets By Classification
****************************************************************/
Array::Subsets By Classification = Func(
    Array( Item Array ),
    Slang( Classifier Function ),
    SubscriptableDatatype( Result ) := Structure(),
)
Returns( SubscriptableDatatype() )
```

- `Result` -- (named, optional) initial result container. Use `GStructure()` for non-string keys, `StructureCase()` for case-sensitive keys.

```slang
@Array::Subsets By Classification(
    [ 1, 2, 3, 4, 5, 6 ],
    \x -> If( Mod( x, 2 ) == 0 ) "Even" : "Odd"
);
// Structure( "Even", [ 2, 4, 6 ]; "Odd", [ 1, 3, 5 ] )
```

---

### Array::Group By

**Shorter alias for `Array::Subsets By Classification`.**

```
/****************************************************************
** Routine: Array::Group By
****************************************************************/
Array::Group By = Func(
    Array( Item Array ),
    Slang( Group By Function ),
    SubscriptableDatatype( Result ) := Structure(),
)
Returns( SubscriptableDatatype() )
```

---

### Array::MultiKey Group By

**Group data by multiple keys, each defined by a lambda.**

```
/****************************************************************
** Routine: Array::MultiKey Group By
****************************************************************/
Array::MultiKey Group By = Func(
    Array( Array ),
    Array( Group Keys ),
    Array( Group Slangs ),
    String( Data Key ) := "Data",
)
Returns( Array() )
```

- `Group Keys` -- array of string key names.
- `Group Slangs` -- parallel array of lambdas (one per key).
- `Data Key` -- (named, optional) key name for the grouped data. Default `"Data"`.

---

### Array::Structure Subsets

**Group an array of structures by a field value. Returns a Structure of arrays.**

```
/****************************************************************
** Routine: Array::Structure Subsets
****************************************************************/
Array::Structure Subsets = Func(
    Array( &Records ),
    String( Key Field ),
)
Returns( Structure(), Error() )
```

---

### Array::Bucket Pairwise

**Bucket elements of B by corresponding elements of A. Optionally aggregate.**

```
/****************************************************************
** Routine: Array::Bucket Pairwise
****************************************************************/
Array::Bucket Pairwise = Func(
    Array( A ),
    Array( B ),
    Slang( Aggregation ) = Slang(),
)
Returns( GStructure() )
```

- `Aggregation` -- (positional, optional) aggregation lambda, e.g. `\x -> Sum( x )`.

```slang
A = [ 1, 1, 2, 1, 3, 3 ];
B = [ 2, 3, 10, 4, 1, 5 ];
@Array::Bucket Pairwise( A, B, \x -> Sum( x ) );
// GStructure( 1, 9; 2, 10; 3, 6 )
```

---

### Array::Element Frequencies

**Returns a GStructure mapping each element to its frequency count.**

```
/****************************************************************
** Routine: Array::Element Frequencies
****************************************************************/
Array::Element Frequencies = Func(
    Array( A ),
)
Returns( GStructure() )
```

```slang
@Array::Element Frequencies( [ "a", "b", "a", "c", "a" ] );
// GStructure( "a", 3; "b", 1; "c", 1 )
```

---

### Array::Most Frequent Elements

**Returns an array of the most frequently occurring elements (handles ties).**

```
/****************************************************************
** Routine: Array::Most Frequent Elements
****************************************************************/
Array::Most Frequent Elements = Func(
    Array( A ),
)
Returns( Array() )
```

---

### Array::Get Sequential Repeats

**Find runs of consecutive identical elements.**

```
/****************************************************************
** Routine: Array::Get Sequential Repeats
****************************************************************/
Array::Get Sequential Repeats = Func(
    Array( A ),
    Double( Min Run Length ) := 2,
    Double( Tabular Output ) := False,
)
Returns( Array() )
```

- `Min Run Length` -- (named, optional) minimum run length to include. Default 2.
- `Tabular Output` -- (named, optional) if True, returns structures `{| Value, Count |}` instead of arrays.

```slang
@Array::Get Sequential Repeats( [ 1, 3, 4, 4, 5, 5, 2, 2, 1 ] );
// [ [ 4, 4 ], [ 5, 5 ], [ 2, 2 ] ]
```

---

### Array::Factorize Y by X

**Group parallel arrays into a GStructure mapping X values to arrays of corresponding Y values.**

```
/****************************************************************
** Routine: Array::Factorize Y by X
****************************************************************/
Array::Factorize Y by X = Func(
    Array( X ),
    Array( Y ),
)
Returns( GStructure() )
```

---

## Flattening, Splitting, and Reshaping

---

### Array::Flatten

**Recursively flatten nested arrays to a 1D array.**

```
/****************************************************************
** Routine: Array::Flatten
****************************************************************/
Array::Flatten = Func(
    Any( Nested ),
)
Returns( Array() )
```

```slang
@Array::Flatten( [ [ 1 ], [ 2, 3 ], [ [ 4 ] ] ] );
// [ 1, 2, 3, 4 ]
```

---

### Array::Flatten One Level

**Flatten nested arrays by one level only.**

```
/****************************************************************
** Routine: Array::Flatten One Level
****************************************************************/
Array::Flatten One Level = Func(
    Array( Nested ),
)
Returns( Array() )
```

```slang
@Array::Flatten One Level( [ [ 1, 2 ], [ 3, [ 4 ] ] ] );
// [ 1, 2, 3, [ 4 ] ]
```

---

### Array::Flatten Unique

**Flatten, sort, and deduplicate. Optionally with custom ordering.**

```
/****************************************************************
** Routine: Array::Flatten Unique
****************************************************************/
Array::Flatten Unique = Func(
    Any( Nested ),
    Slang( Ordering ) := Slang(),
)
Returns( Array() )
```

---

### Array::Unflatten

**Convert a 1D array back to a multidimensional array given dimension sizes.**

```
/****************************************************************
** Routine: Array::Unflatten
****************************************************************/
Array::Unflatten = Func(
    Array( A ),
    Array( Dimension Sizes ),
)
Returns( Array() )
```

```slang
@Array::Unflatten( [ 1, 2, 3, 4, 5, 6 ], [ 2, 3 ] );
// [ [ 1, 2, 3 ], [ 4, 5, 6 ] ]
```

---

### Array::Split

**Split an array into chunks of at most `SplitSize` elements.**

```
/****************************************************************
** Routine: Array::Split
****************************************************************/
Array::Split = Func(
    Array( Array ),
    Double( SplitSize ),
    Double( Homogenize ) := False,
)
Returns( Array() )
```

- `Homogenize` -- (named, optional) if True, redistribute so chunks are more even in size.

```slang
@Array::Split( [ 0, 1, 2, 3, 4, 5 ], 5, Homogenize := True );
// [ [ 0, 1, 2 ], [ 3, 4, 5 ] ]
```

---

### Array::Bucketize

**Split array evenly into a fixed number of buckets.**

```
/****************************************************************
** Routine: Array::Bucketize
****************************************************************/
Array::Bucketize = Func(
    Array( Array ),
    Double( Bucket Count ),
    Double( Prune Empty ) := True,
)
Returns( Array() )
```

- `Prune Empty` -- (named, optional) remove empty trailing buckets. Default True.

```slang
@Array::Bucketize( [ 1, 2, 3, 4, 5, 6 ], 4 );
// [ [ 1, 2 ], [ 3, 4 ], [ 5 ], [ 6 ] ]
```

---

### Array::Transpose

**Transpose an array of arrays (matrix transpose). Wraps `Functional::UnZip`.**

```
/****************************************************************
** Routine: Array::Transpose
****************************************************************/
Array::Transpose = Func(
    Array( a ),
    Double( Check Subarray Sizes ) := False,
    Double( Transpose of N x 0 is Empty ) := False,
)
Returns( Array() )
```

- `Check Subarray Sizes` -- (named, optional) throw if sub-arrays differ in size.
- `Transpose of N x 0 is Empty` -- (named, optional) return `[]` instead of passthrough if first sub-array is empty.

```slang
@Array::Transpose( [ [ 1, 2 ], [ 3, 4 ] ] );
// [ [ 1, 3 ], [ 2, 4 ] ]
```

---

### Array::Tablify

**Convert a 1D array into a 2D tabular layout (columns or rows).**

```
/****************************************************************
** Routine: Array::Tablify
****************************************************************/
Array::Tablify = Func(
    Array( List ),
    Double( Min Rows ) := 5,
    Double( Max Columns ) := 3,
    Double( Pack ) := True,
    Double( Rowwise ) := False,
    Double( Output Rows ) := False,
    Any( Pad ) := Any(),
)
Returns( Array() )
```

---

### Array::Table Projection

**Select specific columns from a matrix (array of arrays).**

```
/****************************************************************
** Routine: Array::Table Projection
****************************************************************/
Array::Table Projection = Func(
    Array( InputArray ),
    Array( ColumnsToShow ),
)
Returns( Array(), Error() )
```

```slang
@Array::Table Projection( [ [ 1, 2, 3 ], [ 4, 5, 6 ] ], [ 0, 2 ] );
// [ [ 1, 3 ], [ 4, 6 ] ]
```

---

### Array::Delete Column

**Delete a column from a 2D array (array of arrays) in place.**

```
/****************************************************************
** Routine: Array::Delete Column
****************************************************************/
Array::Delete Column = Func(
    Array( &A ),
    Double( Col Index ),
)
Returns()
```

---

### Array::Untabulate

**Convert an array of structures back into an array of arrays with headers.**

```
/****************************************************************
** Routine: Array::Untabulate
****************************************************************/
Array::Untabulate = Func(
    Array( Table ),
    Array( Headings ),
    Default Value = Null,
)
Returns( Array() )
```

---

## Concatenation, Merging, and Modification

---

### Array::Concat

**Concatenate an arbitrary number of arrays (no sort/unique). Use `Array::Union` if you want that.**

```
/****************************************************************
** Routine: Array::Concat
****************************************************************/
Array::Concat = Func(
    Ellipsis( Arrays ),
)
Returns( Array() )
```

```slang
@Array::Concat( [ "b", "a" ], [ "a" ], [] );
// [ "b", "a", "a" ]
```

---

### Array::Interlace Array

**Merge two arrays by alternating elements.**

```
/****************************************************************
** Routine: Array::Interlace Array
****************************************************************/
Array::Interlace Array = Func(
    Array( A ),
    Array( B ),
)
Returns( Array() )
```

```slang
@Array::Interlace Array( [ 1, 2, 3 ], [ 9, 10 ] );
// [ 1, 9, 2, 10, 3 ]
```

---

### Array::Merge

**Merge two arrays, preferring values from Array1 unless they equal an "empty" sentinel.**

```
/****************************************************************
** Routine: Array::Merge
****************************************************************/
Array::Merge = Func(
    Array( Array1 ),
    Array( Array2 ),
    Any( Empty Value ) = Null,
)
Returns( Array() )
```

```slang
@Array::Merge( [ 1, Null, 2 ], [ 3, 4, Null ], Null );
// [ 1, 4, 2 ]
```

---

### Array::Splice

**Perl-style splice: remove/insert elements at arbitrary positions.**

```
/****************************************************************
** Routine: Array::Splice
****************************************************************/
Array::Splice = Func(
    Array( &Array ),
    Double( Offset ) = 0,
    Double( Length ) = -_DBL MIN,
    Ellipsis( List ) = [],
)
Returns( Array() )
```

- `&Array` -- modified in place.
- `Offset` -- start position (negative = from end).
- `Length` -- elements to remove (negative = leave that many at end).
- `List` -- replacement elements (as ellipsis arguments).

Returns the removed elements.

---

### Array::Splice Add In Replacement Array

**Like `Array::Splice` but takes a replacement Array instead of Ellipsis.**

```
/****************************************************************
** Routine: Array::Splice Add In Replacement Array
****************************************************************/
Array::Splice Add In Replacement Array = Func(
    Array( &Array ),
    Double( Offset ) = 0,
    Double( Length ) = -_DBL MIN,
    Array( Replacement Array ) = [],
)
Returns( Array() )
```

```slang
A = [ "a", "b", "c", "d", "e", "f" ];
B = [ "w", "x", "y", "z" ];
@Array::Splice Add In Replacement Array( &A, 2, 3, B );
// A = [ "a", "b", "w", "x", "y", "z", "f" ]
```

---

### Array::Insert After Value

**Insert a new element right after the first occurrence of a value.**

```
/****************************************************************
** Routine: Array::Insert After Value
****************************************************************/
Array::Insert After Value = Func(
    Array( &Array ),
    Any( Value ),
    Any( New Value ),
)
Returns()
```

```slang
A = [ "A", "B", "D" ];
@Array::Insert After Value( A, "B", "C" );
// A = [ "A", "B", "C", "D" ]
```

---

### Array::Swap In Place

**Swap two elements by index.**

```
/****************************************************************
** Routine: Array::Swap In Place
****************************************************************/
Array::Swap In Place = Func(
    Array( &In ),
    Double( Index 1 ),
    Double( Index 2 ),
)
Returns()
```

---

## Array Generation

---

### Array::Indices

**Generate array `[ S, S+I, S+2I, ..., S+(N-1)*I ]`.**

```
/****************************************************************
** Routine: Array::Indices
****************************************************************/
Array::Indices = Func(
    Double( N ),
    Double( S ) = 0,
    Double( I ) = 1,
)
Returns( Array() )
```

```slang
@Array::Indices( 5 );           // [ 0, 1, 2, 3, 4 ]
@Array::Indices( 4, 10, 5 );    // [ 10, 15, 20, 25 ]
```

---

### Array::FillRange

**Generate an array from Begin to End with a given Step.**

```
/****************************************************************
** Routine: Array::FillRange
****************************************************************/
Array::FillRange = Func(
    Double( Begin ),
    Double( End ),
    Double( Step ) = 1,
)
Returns( Array(), Error() )
```

```slang
@Array::FillRange( 6, -4, -3 );  // [ 6, 3, 0, -3 ]
```

---

### Array::Gen Line

**Generate a sequence from Start to End with a given Interval. Supports non-numeric types (Dates, etc.).**

```
/****************************************************************
** Routine: Array::Gen Line
****************************************************************/
Array::Gen Line = Func(
    Any( Start ),
    Any( End ),
    Any( Interval ),
    Double( Include End Always ) := False,
)
Returns( Array() )
```

- `Include End Always` -- (named, optional) if True, append `End` even if it doesn't fall on an interval boundary.

```slang
@Array::Gen Line( 1, 3, 0.5 );
// [ 1, 1.5, 2, 2.5, 3 ]
```

---

### Array::Generate

**Generate an array of N elements by calling a function on each index 0..N-1.**

```
/****************************************************************
** Routine: Array::Generate
****************************************************************/
Array::Generate = Func(
    Double( N ),
    Slang( GenOp ) = Func( x ) x,
)
Returns( Array() )
```

```slang
@Array::Generate( 3 );                         // [ 0, 1, 2 ]
@Array::Generate( 3, \x -> x * x );            // [ 0, 1, 4 ]
@Array::Generate( 3, \x -> Today() + x );      // [ Today, Tomorrow, ... ]
```

---

### Array::ArrayLinspace

**N-point array linearly spaced from Start to End.**

```
/****************************************************************
** Routine: Array::ArrayLinspace
****************************************************************/
Array::ArrayLinspace = Func(
    Double( Start ),
    Double( End ),
    Double( N ) = 100,
)
Returns( Array() )
```

---

### Array::FillArray

**Fill an array with a value. Prefer using `ArrayInitialize` directly.**

```
/****************************************************************
** Routine: Array::FillArray
****************************************************************/
Array::FillArray = Func(
    Double( SizeArray ),
    Any( Value ),
)
Returns( Array() )
```

---

### Array::Repeat

**Repeat an array `Count` times.**

```
/****************************************************************
** Routine: Array::Repeat
****************************************************************/
Array::Repeat = Func(
    Array( Elements ),
    Double( Count ),
)
Returns( Array() )
```

```slang
@Array::Repeat( [ 100, 200 ], 3 );
// [ 100, 200, 100, 200, 100, 200 ]
```

---

### Array::Symmetric

**Generate a symmetric array of numbers centered around a value.**

```
/****************************************************************
** Routine: Array::Symmetric
****************************************************************/
Array::Symmetric = Func(
    Double( Center ) := 0,
    Double( Knot Count ) := Error Value,
    Double( Knot Count Parity ) := Error Value,
    Double( Knot Spacing ) := Error Value,
    Double( Diameter ) := Error Value,
    Double( Round ) := Error Value,
)
Returns( Array() )
```

Specify any 2 of: `Knot Count`, `Knot Spacing`, `Diameter`.

---

## Shuffling and Sampling

---

### Array::Deterministic Shuffle

**Shuffle an array deterministically (reproducible with same seed).**

```
/****************************************************************
** Routine: Array::Deterministic Shuffle
****************************************************************/
Array::Deterministic Shuffle = Func(
    Array( Elements ),
    Double( Seed ) = Double( Today() );
    Double( Ignore Seed ) := False,
)
Returns( Array() )
```

- `Seed` -- (positional with default) seed value.
- `Ignore Seed` -- (named, optional) skip seeding for backward compatibility.

> Max array size: 8,333,333. For larger arrays or in-place shuffling, use `Array::Shuffle In Place Stateless`.

---

### Array::Shuffle In Place

**Fisher-Yates O(n) in-place shuffle. Depends on/modifies global `Random()` state.**

```
/****************************************************************
** Routine: Array::Shuffle In Place
****************************************************************/
Array::Shuffle In Place = Func(
    SubscriptValueVector( &Elements ),
    Double( Seed ) = Double( Today() );
    Double( Ignore Seed ) := False,
    Double( Num Elements ) := Size( Elements ),
)
Returns()
```

- `Num Elements` -- (named, optional) shuffle only this many elements to the end of the array (partial shuffle).

---

### Array::Shuffle In Place Stateless

**Fisher-Yates shuffle that does NOT touch global `Random()` state. Preferred for reproducibility.**

```
/****************************************************************
** Routine: Array::Shuffle In Place Stateless
****************************************************************/
Array::Shuffle In Place Stateless = Func(
    SubscriptValueVector( &Elements ),
    Double( Seed ) = URandomDouble(),
    Double( Num Elements ) := Size( Elements ),
)
Returns()
```

---

### Array::Random Sample

**Randomly sample K elements from a population (without replacement).**

```
/****************************************************************
** Routine: Array::Random Sample
****************************************************************/
Array::Random Sample = Func(
    Array( Population ),
    Double( Sample Size ),
    Double( Seed ) := URandomDouble(),
)
Returns( Array() )
```

---

## Aggregation and Math

---

### Array::Sum

**Sum values, optionally ignoring errors.**

```
/****************************************************************
** Routine: Array::Sum
****************************************************************/
Array::Sum = Func(
    Array( In ),
    Double( DeleteErrors ) = True,
    Slang( MyOwnFilter ) = Slang(),
    Any( Init Value ) := Null,
)
Returns( Double() )
```

- `DeleteErrors` -- (positional, optional) skip error values. Default True.
- `MyOwnFilter` -- (positional, optional) custom filter lambda.
- `Init Value` -- (named, optional) initial accumulator value.

---

### Array::Sums To Within Tolerance

**Checks whether an array sums to a target within absolute/relative tolerance.**

```
/****************************************************************
** Routine: Array::Sums To Within Tolerance
****************************************************************/
Array::Sums To Within Tolerance = Func(
    Array( In ),
    Double( Sum Comparison ) = 0,
    Double( Abs Tolerance ) := 1e-10,
    Double( Rel Tolerance ) := 1e-14,
)
Returns( Double() )
```

---

### Array::Product

**Multiply all elements together.**

```
/****************************************************************
** Routine: Array::Product
****************************************************************/
Array::Product = Func(
    Array( Arr ),
    Any( Default ) = 1,
)
Returns( Any() )
```

- `Default` -- (positional, optional) return this for empty arrays.

```slang
@Array::Product( [ 2, 3, 4 ] );  // 24
@Array::Product( [] );            // 1
```

---

### Array::Running Sum

**Running (cumulative) sum.**

```
/****************************************************************
** Routine: Array::Running Sum
****************************************************************/
Array::Running Sum = Func(
    Array( A ),
)
Returns( Array() )
```

```slang
@Array::Running Sum( [ 1, 0, 1, 0, 1, 0, 1, 0 ] );
// [ 1, 1, 2, 2, 3, 3, 4, 4 ]
```

---

### Array::Sum Record Group

**Group an array of structures by key fields and sum the numeric columns.**

```
/****************************************************************
** Routine: Array::Sum Record Group
****************************************************************/
Array::Sum Record Group = Func(
    Array( &Records ),
    Array( Key Fields ),
    Delimiter = Chr( 3 );
    Double( Fast Validation ) = True,
)
Returns( Array(), Null )
```

> **Warning:** Only works for numeric sum columns. Not safe for non-string key fields due to implicit string casting.

---

### Array::Add Totals

**Append a `"TOTAL"` row to a 2D array, summing numeric columns.**

```
/****************************************************************
** Routine: Array::Add Totals
****************************************************************/
Array::Add Totals = Func(
    Array( &A ),
    Double( Start From Col ) = 1,
)
Returns( Array() )
```

```slang
@Array::Add Totals( &[ [ "A", 1, 2 ], [ "B", 3, 4 ] ], 1 );
// [ [ "A", 1, 2 ], [ "B", 3, 4 ], [ "TOTAL", 4, 6 ] ]
```

---

### Array::Interpolate

**Compute interpolation weights for a value within an array.**

```
/****************************************************************
** Routine: Array::Interpolate
****************************************************************/
Array::Interpolate = Func(
    Array( A ),
    Any( X ),
    Double( Interpolation Type ) := _Interpolate Only,
    Double( Return All Possible ) := False,
    Double( Extrapolate Flat ) := False,
)
Returns( Array() )
```

---

### Array::Interpolate Map X to Y

**Linear interpolation mapping: given parallel X/Y arrays and an x-value, return the interpolated y-value.**

```
/****************************************************************
** Routine: Array::Interpolate Map X to Y
****************************************************************/
Array::Interpolate Map X to Y = Func(
    Double( xv ),
    Array( x ),
    Array( y ),
)
Returns( Double() )
```

---

### Array::Get Map X to Y Interpolator

**Returns a functor for repeated interpolation between parallel X/Y arrays.**

```
/****************************************************************
** Routine: Array::Get Map X to Y Interpolator
****************************************************************/
Array::Get Map X to Y Interpolator = Func(
    Array( x ),
    Array( y ),
)
Returns( GsDt() )
```

---

## Indexing and Rotation

---

### Array::Index

**Like `A[x]`, but supports negative indexing from the end.**

```
/****************************************************************
** Routine: Array::Index
****************************************************************/
Array::Index = Func(
    Array( A ),
    Double( I ),
)
Returns( Any() )
```

```slang
@Array::Index( [ 10, 20, 30 ], -1 );  // 30
@Array::Index( [ 10, 20, 30 ], -2 );  // 20
```

---

### Array::Circular Index

**Like `Array::Index`, but wraps around the array boundaries.**

```
/****************************************************************
** Routine: Array::Circular Index
****************************************************************/
Array::Circular Index = Func(
    Array( A ),
    Double( I ),
)
Returns( Any() )
```

---

### Array::Rotate

**Move N elements from the front to the back (positive N) or back to front (negative N).**

```
/****************************************************************
** Routine: Array::Rotate
****************************************************************/
Array::Rotate = Func(
    Array( A ),
    Double( N ),
)
Returns( Array() )
```

```slang
@Array::Rotate( [ 1, 2, 3, 4, 5 ], 2 );
// [ 3, 4, 5, 1, 2 ]
```

---

### Array::Shift

**Like `Array::Rotate`, but replaced slots are filled with a Fill value instead of wrapping.**

```
/****************************************************************
** Routine: Array::Shift
****************************************************************/
Array::Shift = Func(
    Array( A ),
    Double( N ),
    Any( Fill ) := Error Value,
)
Returns( Array() )
```

```slang
@Array::Shift( [ 1, 2, 3 ], 1 );
// [ 2, 3, Error Value ]
```

---

## Comparison and Equality

---

### Array::Equals Ignore Order

**True if two arrays contain the same elements with the same multiplicity, regardless of order.**

```
/****************************************************************
** Routine: Array::Equals Ignore Order
****************************************************************/
Array::Equals Ignore Order = Func(
    Array( A1 ),
    Array( A2 ),
)
Returns( Double() )
```

---

### Array::Starts With

**True if the second array is a prefix of the first.**

```
/****************************************************************
** Routine: Array::Starts With
****************************************************************/
Array::Starts With = Func(
    Array( A1 ),
    Array( A2 ),
    Double( Reverse ) = False,
)
Returns( Double() )
```

---

### Array::Ends With

**True if the second array is a suffix of the first.**

```
/****************************************************************
** Routine: Array::Ends With
****************************************************************/
Array::Ends With = Func(
    Array( A1 ),
    Array( A2 ),
)
Returns( Double() )
```

---

### Array::Compare

**3-way comparison of two arrays (like `StrCmp` for strings).**

```
/****************************************************************
** Routine: Array::Compare
****************************************************************/
Array::Compare = Func(
    Array( a ),
    Array( b ),
)
Returns( Double() )
```

Returns -1, 0, or 1.

---

## Conversion and Structure Operations

---

### Array::Array from Array of Structs

**Extract a single field from an array of structures into a flat array. Also aliased as `Array::Pluck`.**

```
/****************************************************************
** Routine: Array::Array from Array of Structs
****************************************************************/
Array::Array from Array of Structs = Func(
    Array( Array of Structures ),
    Element Name,
    Double( Skip Missing Elements ) := False,
)
Returns( Array() )
```

- `Skip Missing Elements` -- (named, optional) skip structures missing the key. Default False (inserts Null).

```slang
Data = [ {| Name := "Alice", Age := 30 |}, {| Name := "Bob", Age := 25 |} ];
@Array::Array from Array of Structs( Data, "Name" );
// [ "Alice", "Bob" ]

// Shorthand alias:
@Array::Pluck( Data, "Name" );
```

---

### Array::StructureUnion

**Union an array of structures together. First value seen for a key wins.**

```
/****************************************************************
** Routine: Array::StructureUnion
****************************************************************/
Array::StructureUnion = Func(
    Array( Structures ),
)
Returns( ComponentValueStructure() )
```

```slang
@Array::StructureUnion( [ {| a := 1 |}, {| a := 3, b := 2 |} ] );
// {| a := 1, b := 2 |}
```

---

### Array::Structure Diff

**Compare two arrays of structures, returning which fields differ at which row indices.**

```
/****************************************************************
** Routine: Array::Structure Diff
****************************************************************/
Array::Structure Diff = Func(
    Array( Old Value ),
    Array( New Value ),
)
Returns( Structure() )
```

---

### Array::Invert To GStructure

**Convert `Array[i] = x` into `GStructure[x] = i`.**

```
/****************************************************************
** Routine: Array::Invert To GStructure
****************************************************************/
Array::Invert To GStructure = Func(
    Array( arr ),
)
Returns( GStructure() )
```

---

### Array::Array to Associative Array

**Convert an array of strings into a Structure mapping each string to its last index.**

```
/****************************************************************
** Routine: Array::Array to Associative Array
****************************************************************/
Array::Array to Associative Array = Func(
    Array( Inp Array ),
    Double( Case Sensitive ) := False,
)
Returns( Structure(), StructureCase() )
```

---

## Null and Error Handling

---

### Array::Remove Nulls

**Recursively remove all Null elements.**

```
/****************************************************************
** Routine: Array::Remove Nulls
****************************************************************/
Array::Remove Nulls = Func(
    Any( A ),
)
Returns( Any() )
```

```slang
@Array::Remove Nulls( [ 1, 2, Null, 3, [ 4, Null, 5 ] ] );
// [ 1, 2, 3, [ 4, 5 ] ]
```

---

### Array::Remove Trailing Nulls

**Remove trailing Null elements.**

```
/****************************************************************
** Routine: Array::Remove Trailing Nulls
****************************************************************/
Array::Remove Trailing Nulls = Func(
    Array( Array ),
)
Returns( Array() )
```

```slang
@Array::Remove Trailing Nulls( [ 1, Null, "No.3", 4, Null, Null ] );
// [ 1, Null, "No.3", 4 ]
```

---

### Array::Remove Trailing By Property

**Remove trailing elements matching a predicate.**

```
/****************************************************************
** Routine: Array::Remove Trailing By Property
****************************************************************/
Array::Remove Trailing By Property = Func(
    Array( Array ),
    Slang( Property ),
)
Returns( Array() )
```

---

## Sizing and Padding

---

### Array::Ensure Size

**Returns a copy extended or truncated to a given size.**

```
/****************************************************************
** Routine: Array::Ensure Size
****************************************************************/
Array::Ensure Size = Func(
    Array( Existing Array ),
    Double( New Size ),
    Default Element,
)
Returns( Array() )
```

---

### Array::Ensure Wrapped

**If the input is already an array, return it. Otherwise wrap it in a 1-element array.**

```
/****************************************************************
** Routine: Array::Ensure Wrapped
****************************************************************/
Array::Ensure Wrapped = Func(
    Any( Input ),
)
Returns( Array() )
```

```slang
@Array::Ensure Wrapped( 42 );        // [ 42 ]
@Array::Ensure Wrapped( [ 1, 2 ] );  // [ 1, 2 ]
```

---

## Packing, Combinatorics, and Other

---

### Array::Cartesian Product

**Cartesian product of two arrays.**

```
/****************************************************************
** Routine: Array::Cartesian Product
****************************************************************/
Array::Cartesian Product = Func(
    Array( A ),
    Array( B ),
)
Returns( Array() )
```

---

### Array::Cartesian Product Many

**Cartesian product of an arbitrary number of arrays.**

```
/****************************************************************
** Routine: Array::Cartesian Product Many
****************************************************************/
Array::Cartesian Product Many = Func(
    Ellipsis( Arrays ) = [],
)
Returns( Array() )
```

---

### Array::Cross List

**All combinations from an array of arrays.**

```
/****************************************************************
** Routine: Array::Cross List
****************************************************************/
Array::Cross List = Func(
    Array( Orig ),
)
Returns( Array() )
```

```slang
@Array::Cross List( [ [ 1, 2 ], [ "a", "b" ] ] );
// [ [ 1, "a" ], [ 2, "a" ], [ 1, "b" ], [ 2, "b" ] ]
```

---

### Array::Power Set

**All subsets of an array (power set).**

```
/****************************************************************
** Routine: Array::Power Set
****************************************************************/
Array::Power Set = Func(
    Array( Set ),
)
Returns( Array() )
```

> Can be slow for sets with > 20 elements.

---

### Array::Power Series

**Generate power series terms from an array of variables.**

```
/****************************************************************
** Routine: Array::Power Series
****************************************************************/
Array::Power Series = Func(
    Array( Vars ),
    Any( Var Power ),
)
Returns( GStructure() )
```

---

### Array::Minimal Height Tree

**Build a minimal-height tree (nested arrays) from a flat collection.**

```
/****************************************************************
** Routine: Array::Minimal Height Tree
****************************************************************/
Array::Minimal Height Tree = Func(
    Array( Collection ),
    Double( Branch Factor ) := 2,
)
Returns( Array() )
```

---

### Array::Bin Pack

**Pack objects into minimum number of bins with a given capacity (first-fit-decreasing heuristic).**

```
/****************************************************************
** Routine: Array::Bin Pack
****************************************************************/
Array::Bin Pack = Func(
    Array( Array ),
    Double( BinSize ),
    Array( &Unpacked ),
    Slang( Size ) = \Any(x) -> Switch( TypeOf( x ), "Double", x, Size( x ) ),
)
Returns( Array() )
```

- `&Unpacked` -- (by reference) receives items that exceed bin size.
- `Size` -- (positional, optional) function mapping elements to their "size".

---

### Array::Bin Pack Fixed Count

**Pack objects into a fixed number of bins, minimizing the maximum bin capacity.**

```
/****************************************************************
** Routine: Array::Bin Pack Fixed Count
****************************************************************/
Array::Bin Pack Fixed Count = Func(
    Array( Array ),
    Double( Bin Count ),
    Slang( Size ) = Func( Any(x) ) Switch( TypeOf( x ), "Double", x, Size( x ) ),
)
Returns( Array() )
```

---

### Array::Simple Bucket

**Split an array into sub-arrays by a cumulative size threshold.**

```
/****************************************************************
** Routine: Array::Simple Bucket
****************************************************************/
Array::Simple Bucket = Func(
    SubscriptableDatatype( Subscriptable ),
    Double( Size Threshold ),
    Slang( Size Function ) = Func( x ) x,
)
Returns( Array() )
```

---

### Array::Bitwise Or

**Element-wise bitwise OR of two arrays of doubles.**

```
/****************************************************************
** Routine: Array::Bitwise Or
****************************************************************/
Array::Bitwise Or = Func(
    Array( A ),
    Array( B ),
)
Returns( Array() )
```

---

### Array::Component Max

**Element-wise max with a number.**

```
/****************************************************************
** Routine: Array::Component Max
****************************************************************/
Array::Component Max = Func(
    Array( Array ),
    Double( Number ),
    Double( Validate DataType ) := True,
)
Returns( Array() )
```

```slang
@Array::Component Max( [ -1, 1, 2, 3, 0, -4, 9, 7 ], 1 );
// [ 1, 1, 2, 3, 1, 1, 9, 7 ]
```

---

### Array::Component Min

**Element-wise min with a number.**

```
/****************************************************************
** Routine: Array::Component Min
****************************************************************/
Array::Component Min = Func(
    Array( Array ),
    Double( Number ),
    Double( Validate DataType ) := True,
)
Returns( Array() )
```

---

### Array::Min Index

**Returns `{| Value, Index |}` for the minimum element.**

```
/****************************************************************
** Routine: Array::Min Index
****************************************************************/
Array::Min Index = Func(
    Array( List ),
)
Returns( Structure() )
```

---

### Array::Max Index

**Returns `{| Value, Index |}` for the maximum element.**

```
/****************************************************************
** Routine: Array::Max Index
****************************************************************/
Array::Max Index = Func(
    Array( List ),
)
Returns( Structure() )
```

---

### Array::Arg Min

**Returns the element (index and value) that minimizes a function.**

```
/****************************************************************
** Routine: Array::Arg Min
****************************************************************/
Array::Arg Min = Func(
    Array( InputList ),
    Slang( F ) = \x -> x,
)
Returns( Structure() )
```

```slang
@Array::Arg Min( [ 1, -5, 2 ], \x -> Abs( x ) );
// {| Index := 0, Value := 1 |}
```

---

### Array::Arg Max

**Returns the element (index and value) that maximizes a function.**

```
/****************************************************************
** Routine: Array::Arg Max
****************************************************************/
Array::Arg Max = Func(
    Array( InputList ),
    Slang( F ) = \x -> x,
)
Returns( Structure() )
```

```slang
@Array::Arg Max( [ 1, -5, 2 ], \x -> Abs( x ) );
// {| Index := 1, Value := -5 |}
```

---

### Array::PrintLine

**Print array elements on a single line with formatting.**

```
/****************************************************************
** Routine: Array::PrintLine
****************************************************************/
Array::PrintLine = Func(
    Array( A ),
    String( Sep ) = " ",
    Any( Width ) = Null,
    Any( Row ) = Null,
    Any( Flags ) = Null,
    Any( CustomError ) = Null,
    Double( Final Space ) := True,
)
Returns()
```

---

### Array::Summarise Strings

**Summarise an array of strings, e.g. `[ "Pear", "Peach", "Persimmon" ]` becomes `"Pear+2"`.**

```
/****************************************************************
** Routine: Array::Summarise Strings
****************************************************************/
Array::Summarise Strings = Func(
    Array( Strings ),
)
Returns( String() )
```

---

### Array::DownSample

**Down-sample an array by a step.**

```
/****************************************************************
** Routine: Array::DownSample
****************************************************************/
Array::DownSample = Func(
    Array( A ),
    Double( Step ) = 1,
    Double( Begin ) = 0,
    End = NULL,
)
Returns( Array(), Error() )
```

---

### Array::DeleteLambda

**Remove the first occurrence of a specific lambda from an array (matched by `_uniqueid`).**

```
/****************************************************************
** Routine: Array::DeleteLambda
****************************************************************/
Array::DeleteLambda = Func(
    Array( &a ),
    Slang( l ),
)
Returns()
```

---

### Array::TransposeArrayVectors

**Transpose an array of GsDtVectors.**

```
/****************************************************************
** Routine: Array::TransposeArrayVectors
****************************************************************/
Array::TransposeArrayVectors = Func(
    Array( Vectors ),
)
Returns( Array() )
```

---

### Array::TransposeArrayArrayVectors

**Transpose an array of arrays of GsDtVectors to an array of GsDtMatrices.**

```
/****************************************************************
** Routine: Array::TransposeArrayArrayVectors
****************************************************************/
Array::TransposeArrayArrayVectors = Func(
    Array( X ),
)
Returns( Array() )
```

---

# Part 2: Built-in Array Functions

No `Link()` required. These are native Slang functions.

---

## ArrayInsert

**Insert null slots into an array before a given index.**

```
ArrayInsert( Array, Index [, Count ] ) => (modifies Array in place)
```

- `Index`: position to insert before (0-based).
- `Count`: number of null elements to insert (default 1).

```slang
A = [ "a", "b", "c" ];
ArrayInsert( A, 1, 2 );
// A = [ "a", Null, Null, "b", "c" ]
```

---

## ArrayDelete

**Remove elements from an array.**

```
ArrayDelete( Array, Index, Count ) => (modifies Array in place)
```

```slang
A = [ 1, 2, 3, 4, 5 ];
ArrayDelete( A, 1, 2 );
// A = [ 1, 4, 5 ]
```

---

## ArrayExtract

**Extract a sub-array.**

```
ArrayExtract( Array, Index, Count ) => Array
```

Returns a new array; original is unchanged.

```slang
A = [ 10, 20, 30, 40, 50 ];
Sub = ArrayExtract( A, 2, 3 );
// Sub = [ 30, 40, 50 ]
```

---

## ArrayConcat

**Append one array onto another in place.**

```
ArrayConcat( TargetArray, SourceArray ) => (modifies TargetArray)
```

```slang
A = [ 1, 2 ];
B = [ 3, 4 ];
ArrayConcat( A, B );
// A = [ 1, 2, 3, 4 ]
```

---

## Sort

**Sort an array in place (ascending).**

```
Sort( Array ) => (modifies Array in place)
```

```slang
A = [ 3, 1, 4, 1, 5 ];
Sort( A );
// A = [ 1, 1, 3, 4, 5 ]
```

---

## ArrayUnique

**Remove duplicate elements from an array.**

```
ArrayUnique( Array, SortFirst ) => (modifies Array in place)
```

- `SortFirst`: pass `True` to sort the array before deduplication.

```slang
A = [ 3, 1, 2, 1, 3 ];
ArrayUnique( A, True );
// A = [ 1, 2, 3 ]
```

---

## SortTable

**Sort an array of structures by component keys.**

```
SortTable( Array, KeyArray ) => (modifies Array in place)
```

- `KeyArray`: array of string keys to sort by.

```slang
Data = [
    {| "Name" := "Bob", "Age" := 30 |},
    {| "Name" := "Alice", "Age" := 25 |}
];
SortTable( Data, [ "Name" ] );
// Data sorted: Alice, then Bob
```

---

## TableInit

**Create an array of structures from tabular data.**

```
TableInit( Array ) => Array of Structures
```

First sub-array defines column headers; subsequent sub-arrays are rows.

```slang
T = TableInit( [
    [ "Name", "Score" ],
    [ "Alice", 95 ],
    [ "Bob", 87 ]
] );
// T[ 0 ].Name = "Alice", T[ 0 ].Score = 95
```

---

## MapCar

**Apply a function to every element, returning a new array.**

```
MapCar( Function, Array ) => Array
```

```slang
Squared = MapCar( \X -> X * X, [ 1, 2, 3, 4 ] );
// Squared = [ 1, 4, 9, 16 ]
```

---

## Sum

**Sum all numeric elements of an array.**

```
Sum( Array ) => Double
```

```slang
Total = Sum( [ 10, 20, 30 ] );
// Total = 60
```

---

## Size (on Arrays)

**Get the number of elements.**

```
Size( Array ) => Double
```

```slang
Size( [ "a", "b", "c" ] );        // 3
Size( [] );                        // 0
```

---

## ForEach

**Iterate over all elements.**

```
ForEach( Element, Array ) { ... }
ForEach( &Element, Array ) { ... }   // modifiable reference
```

```slang
ForEach( Item, [ 1, 2, 3 ] )
{
    Print( Item, "\n" );
};
```

---

## Concatenation Operator (`++`)

**Create a new array from two arrays.**

```slang
C = [ 1, 2 ] ++ [ 3, 4 ];
// C = [ 1, 2, 3, 4 ]
```

---

## Append Operator (`&=`)

**Append a single element to an array.**

```slang
A = [ 1, 2 ];
A &= 3;
// A = [ 1, 2, 3 ]
```

---

## ComponentExists (on Arrays)

**Check if an index exists.**

```slang
A = [ 10, 20, 30 ];
ComponentExists( A, 2 );          // True
ComponentExists( A, 5 );          // False
```

---

## RotateArray

**Rotate an array by a given count.**

```
RotateArray( Array, Count ) => Array
```

- Positive `Count` rotates left; negative rotates right.
- If `Abs( Count )` exceeds array size, it wraps via `Mod`.

```slang
RotateArray( [ 1, 2, 3, 4, 5 ], 2 );
// [ 3, 4, 5, 1, 2 ]

RotateArray( [ 1, 2, 3, 4, 5 ], -1 );
// [ 5, 1, 2, 3, 4 ]
```

---

## ArrayInitialize

**Create an array of N elements, all set to the same value.**

```
ArrayInitialize( N, Value ) => Array
```

```slang
Zeros = ArrayInitialize( 5, 0 );
// [ 0, 0, 0, 0, 0 ]

Names = ArrayInitialize( 3, "unknown" );
// [ "unknown", "unknown", "unknown" ]
```

---

## ArrayCartesianProduct

**Compute the Cartesian product of two arrays.**

```
ArrayCartesianProduct( Array1, Array2 ) => Array
```

Returns an array of all pairs.

```slang
ArrayCartesianProduct( [ 1, 2 ], [ "a", "b" ] );
// [ [ 1, "a" ], [ 1, "b" ], [ 2, "a" ], [ 2, "b" ] ]
```

---

## ArrayTranspose

**Transpose an array of arrays (matrix transpose).**

```
ArrayTranspose( Array ) => Array
```

The inner array at index 0 determines the result size.

```slang
ArrayTranspose( [ [ 1, 2, 3 ], [ 4, 5, 6 ] ] );
// [ [ 1, 4 ], [ 2, 5 ], [ 3, 6 ] ]
```

---

## FindSubArray

**Find where one array exists inside another (KMP search).**

```
FindSubArray( SearchIn, SearchFor [, Start] ) => Double
```

Returns the 0-based index where `SearchFor` begins in `SearchIn`, or `-1` if not found.

```slang
FindSubArray( [ 1, 2, 3, 4, 5 ], [ 3, 4 ] );    // 2
FindSubArray( [ 1, 2, 3 ], [ 9, 9 ] );           // -1
```

---

## KeysToStruct

**Convert an array of strings into a Structure counting occurrences.**

```
KeysToStruct( Array ) => Structure
```

Keys are the strings; values are counts of how many times each appears.

```slang
KeysToStruct( [ "a", "b", "a", "c", "a" ] );
// {| "a" := 3, "b" := 1, "c" := 1 |}
```

---

## Array2DToStruct

**Convert a 2D array of strings into a Structure counting occurrences.**

```
Array2DToStruct( Array2D ) => Structure
```

```slang
Array2DToStruct( [ [ "a", "b" ], [ "a", "c" ] ] );
// {| "a" := 2, "b" := 1, "c" := 1 |}
```

---

## Array2DFlattenUnique

**Flatten a 2D array into a sorted 1D array of unique elements.**

```
Array2DFlattenUnique( Array2D ) => Array
```

```slang
Array2DFlattenUnique( [ [ "c", "a" ], [ "a", "b" ] ] );
// [ "a", "b", "c" ]
```

---

## Array3DToStruct

**Convert a 3D array of strings into a Structure counting occurrences.**

```
Array3DToStruct( Array3D ) => Structure
```

---

## Array3DFlattenUnique

**Flatten a 3D array into a sorted 1D array of unique elements.**

```
Array3DFlattenUnique( Array3D ) => Array
```

---

## Back

**Get the last element of an array (or offset from the end).**

```
Back( Value [, Offset] ) => Any
```

- `Offset` defaults to 0 (last element). `Offset` of 1 gives second-to-last, etc.

```slang
Back( [ 10, 20, 30 ] );                     // 30
Back( [ 10, 20, 30 ], 1 );                  // 20
```

---

## Sum (on Arrays)

**Sum all values in a container (Array, Vector, Structure, GStructure).**

```
Sum( Container [, InitValue] ) => Any
```

Uses `+=` to accumulate. For string arrays, concatenates.

```slang
Sum( [ 1, 2, 3 ] );                         // 6
Sum( [ 1, 2, 3 ], 10 );                     // 16
Sum( [ "a", "b", "c" ] );                   // "abc"
Sum( [ "a", "b" ], "@" );                   // "@ab"
```

---

## Array::keys

**Get the indices of an array as an array.**

```
Array::keys( Array ) => Array
```

---

## Array::values

**Get the values of an array (returns the same array).**

```
Array::values( Array ) => Array
```

---

## Array::unsortedkeys

**Get the indices of an array in insertion order.**

```
Array::unsortedkeys( Array ) => Array
```

---

## TypedStructureToArray

**Convert a Typed Structure instance into an array.**

```
TypedStructureToArray( TypedStructure [, Template] ) => Array
```

---

## IsKindOf

**Check if a value's base type matches a given type name.**

```
IsKindOf( Derived, BaseType ) => Double (True/False)
```

```slang
IsKindOf( Array(), "SubscriptValueVector" );   // True
IsKindOf( Structure(), "StringValueStructure" ); // True
```

---

## DataTypeOf

**Get the type name of a value (works for GsDt types too).**

```
DataTypeOf( Expr ) => String
```

Unlike `TypeOf()`, this also works for GsDt types.

```slang
DataTypeOf( [ 1, 2, 3 ] );                  // "Array"
DataTypeOf( {| "A" := 1 |} );               // "Structure"
```

---

## TypeOf

**Get the type name of a value.**

```
TypeOf( Expr ) => String
```

> **Note:** Prefer `DataTypeOf()` for GsDt type support.

```slang
TypeOf( "hello" );                           // "String"
TypeOf( 42 );                                // "Double"
```

---

## See Also

- [workingWithArrays.md](workingWithArrays.md) -- full guide with patterns and examples
- `.github/builtins.md` -- complete built-in function reference
- `.github/structures/` -- structures are often used with arrays
