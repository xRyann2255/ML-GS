# String Functions -- Quick Reference

A comprehensive lookup of string functions in Slang. For detailed examples see `examples.md`; for a conceptual walkthrough see `workingWithStrings.md`.

This file covers two categories:

1. **Library Functions** (`_LIB String Functions`) -- require `Link( "_LIB String Functions" )` and are called with the `@String::` prefix. These are the most commonly used string utilities.
2. **Built-in Functions** -- available in any script, no `Link()` required.

> **Fundamentals reminder:**
> - `Size( Str )` returns the length (number of characters) of a string.
> - Strings are **0-based indexed**: `Str[ 0 ]` is the first character, `Str[ Size( Str ) - 1 ]` is the last.
> - Indexing a string returns a **length-1 string** (not a character type): `"hello"[ 1 ]` is `"e"`.
> - Strings support slice notation: `Str[: Start, End :]` extracts a range (0-based, inclusive).
> - Concatenation: `"a" + "b"` produces `"ab"`. Append in place: `S &= "more"`.
> - String comparison with `==` / `!=` is **case-insensitive** by default.
> - For case-sensitive comparison use `StrCmp()`.
> - Individual characters can be assigned: `S[ 0 ] = "H"` modifies in place.

---

# Part 1: Library Functions (`_LIB String Functions`)

To use any function in this section, your script must include:

```slang
Link( "_LIB String Functions" );
```

All functions are called with the `@String::` prefix, e.g. `@String::Reverse( "hello" )`.

Also see `_LIB String Functions 2` for additional utilities.

---

## Table of Contents -- Library Functions

| Category | Functions |
|----------|-----------|
| **Tokenizing & Splitting** | StrTok, SplitMulti, StrSplitRecurse, StrSplitTrim, StrSplitDelims, StrSplitOnWord, SplitBySize, Split Regex, Shell Split |
| **Joining & Formatting Arrays** | ArrayToString, StrJoin, List with Commas, Join Array With Ellipsis, Join Multiline |
| **Searching & Matching** | Count, StrPosRev, StrLastPos, Pos Regex, Find Match, Search Strings |
| **Prefix / Suffix / Contains** | Shared Prefix, Remove Prefix, Remove Prefix Strict, Remove Suffix, Remove Suffix Strict, Begins With Any, Ends With Any, Contains Any, StrContains By Word, StrBegins By Word |
| **Validation & Classification** | Is Digits, Is Numeric, Is Percentage, Is AlphaNumeric, Is AlphaNumeric Upper, Is Text, Is Date, Is Blank |
| **Case Conversion & Naming** | CapUnderscoreToWords, WordsToCapUnderscore, WordsToJavaStyleVariableNames, UnderscoreToWords, WordsToUnderscore, SplitOnCapitals, Capitalize as Proper Noun, Camelize, DeCamelize, Start Case, StrUpper Nth Char |
| **Wrapping & Indentation** | Wrap Around, Wrap On Words, Indent, Nested Indent, DeTab |
| **Truncation & Fitting** | Truncate, Abbreviate, Fit To Length, Fit to Length with Mush, Fit To Length By Split, Digest |
| **Numeric Conversion** | StringToDouble, Number To English, English To Number, Cardinal To Ordinal |
| **Base Encoding** | IntegerToBase36, Base36ToInteger, IntegerToAlphaNumCode, AlphaNumCodeToInteger, Encode Base36, Decode Base36 |
| **String Similarity** | Convolution, Max Convolution, Levenshtein Distance, Closest String, Comparison Ratio |
| **Template / Variable Substitution** | FillIn From Structure, Extract To Structure, Replace Variables, Replace Word |
| **Character-Level Utilities** | Char Not In String, Convert to Valid Chars, NonPrintableCharExist, ReplaceUnprintableChars, RemoveUnprintableChars, JSON Escape, Condense Whitespace, Reverse, StrPad, TrimZero, Strip Leading Zeros, Empty To Null |
| **Multi-line / Columnar** | StrVerticalSlice, StrVerticalGlue, Head Lines, Tail Lines, Print onto End of Pad |
| **Random String Generation** | Random Base10, Random Base16, Random Base32, Random Base36, Random Base64 |
| **Packing / Serialization** | Length Prefix Pack, Length Prefix Unpack, Unpack, Histogram, ASCII XY Graph |
| **Sorting** | Natural Sort Order |

---

## Tokenizing & Splitting

---

### String::StrTok

**Tokenize a string one token at a time (stateful, like C `strtok`).**

```
String::StrTok = Func(
    Any( Arg ),                             // String on first call, Null on subsequent calls
    String( Delims ),                       // Delimiter characters (each char is a delimiter)
    Double( Use Leading Delims ) := False,  // Whether to return empty tokens for leading delims
)
Returns( String(), Null )
```

Returns the next token, or `Null` when no more tokens remain. Internal state is **global** -- prefer `SplitMulti` for concurrent use.

```slang
Token = @String::StrTok( "First.Second,Third", ".," );  // "First"
Token = @String::StrTok( Null, ".," );                   // "Second"
Token = @String::StrTok( Null, ".," );                   // "Third"
Token = @String::StrTok( Null, ".," );                   // Null

// With leading delimiters:
Token = @String::StrTok( "..First.Second", ".," , Use Leading Delims := True );
// ""  (empty token for the leading delimiter)
```

---

### String::SplitMulti

**Split on multiple single-character delimiters at once (non-recursive, fast).**

```
String::SplitMulti = Func(
    String( String ),                   // String to split
    String( Chars ),                    // Characters to split on (each char is a delimiter)
    Double( FilterBlanks ) = False,     // If True, remove empty strings from result
)
Returns( Array() )
```

Functionally equivalent to `StrSplitRecurse` but faster because it avoids recursion.

```slang
@String::SplitMulti( "abc  def.ghi", " ." );
// [ "abc", "", "def", "ghi" ]

@String::SplitMulti( "abc  def.ghi", " .", True );
// [ "abc", "def", "ghi" ]
```

---

### String::StrSplitRecurse

**Split on multiple single-character delimiters (recursive implementation).**

```
String::StrSplitRecurse = Func(
    String( S ),            // String to split
    String( Delim ),        // Characters to split on
)
Returns( Array() )
```

Prefer `SplitMulti` for better performance. Each character in `Delim` is treated as a separate delimiter.

```slang
@String::StrSplitRecurse( "a+b-c", "-+" );
// [ "a", "b", "c" ]
```

---

### String::StrSplitTrim

**Split then trim whitespace from each part, optionally dropping empties.**

```
String::StrSplitTrim = Func(
    String( Data ),                                 // The string to split
    String( Split Char ),                           // Single-char delimiter
    Double( Skip Empty ) := True,                   // If True, omit empty results
    Double( Trim Sides ) := _Leading | _Trailing,   // Which sides to trim
)
Returns( Array() )
```

```slang
@String::StrSplitTrim( " xa x x x  b  x", "x", Skip Empty := True );
// [ "a", "b" ]

@String::StrSplitTrim( " xa x x x  b  x", "x", Skip Empty := False );
// [ "", "a", "", "b" ]
```

---

### String::StrSplitDelims

**Split on delimiter characters, but honour paired delimiters (brackets, quotes, etc.).**

```
String::StrSplitDelims = Func(
    String,                             // String to split
    SplitChars,                         // Character(s) to split on
    LeftDelims,                         // Left delimiter character(s)
    RightDelims,                        // Right delimiter character(s)
    StripDelims = False,                // Strip delimiters from output
    FilterBlanks = False,               // Exclude empty strings
    IgnoreDoubleRightDelims = False,    // Skip instances of exactly 2 right delimiters
    IgnoreBeforeDelim = True,           // Ignore text before a left delimiter
)
Returns( Array(), Null )
```

Returns `Null` if there is no matching right delimiter. Will not split on a `SplitChar` if it is inside a delimiter pair.

```slang
@String::StrSplitDelims( "First{A:On;B:Off};Second{C:True}", ";", "{", "}" );
// [ "{A:On;B:Off}", "{C:True}" ]

@String::StrSplitDelims( "'foo' \t  2 bar", " \t", "'", "'", True, True );
// [ "foo", "2", "bar" ]
```

---

### String::StrSplitOnWord

**Split on a multi-character delimiter (word-based split).**

```
String::StrSplitOnWord = Func(
    String( In ),                       // The string to split
    String( Splitter ),                 // The word/substring to split on
    Double( TrimResults ) = False,      // Trim whitespace from resulting substrings
    Double( Filter Blanks ) := False,   // Remove blank strings from result
)
Returns( Array() )
```

```slang
@String::StrSplitOnWord( "apple/banana/apple", "banana" );
// [ "apple/", "/apple" ]

@String::StrSplitOnWord( "apple\n\t banana \t\napple", "banana", True );
// [ "apple", "apple" ]

@String::StrSplitOnWord( "one, two, three,    , five", ", ", True, Filter Blanks := True );
// [ "one", "two", "three", "five" ]
```

---

### String::SplitBySize

**Split a string into fixed-width chunks.**

```
String::SplitBySize = Func(
    String( S ),
    Double( Width ),
)
Returns( Array() )
```

```slang
@String::SplitBySize( "foobarbaz", 3 );
// [ "foo", "bar", "baz" ]

@String::SplitBySize( "asdf", 3 );
// [ "asd", "f" ]
```

---

### String::Split Regex

**Split a string on a regular expression, with options for including matches and trimming.**

```
String::Split Regex = Func(
    String( s ),
    RegEx( re ),
    Double( Include Matches )       := False,
    Double( Trim Elements )         := False,
    Double( Remove Blank Elements ) := False,
)
Returns( Array() )
```

```slang
@String::Split Regex( "The finex quick fine brown fine fox", RegExP( "fine" ) );
// [ "The ", "x quick ", " brown ", " fox" ]

@String::Split Regex( "The finex quick fine fox", RegExP( "fine" ), Include Matches := True );
// [ "The ", "fine", "x quick ", "fine", " fox" ]

@String::Split Regex( " HOLD abc HOLD xyz HOLD ", RegExP( "HOLD" ), Trim Elements := True, Remove Blank Elements := True );
// [ "abc", "xyz" ]
```

---

### String::Shell Split

**POSIX-compliant shell-style tokenization (handles single/double quotes, backslash escapes).**

```
String::Shell Split = Func(
    String( Input ),
)
Returns( Array( ... ), Error() )
```

Splits a string exactly as a POSIX shell would: whitespace separates tokens, single quotes preserve literal characters, double quotes allow backslash escaping, backslash-newline is a line continuation.

Returns an `Error()` if quotes or escapes are unfinished.

```slang
@String::Shell Split( "hello world" );
// [ "hello", "world" ]

@String::Shell Split( "'hello world' foo" );
// [ "hello world", "foo" ]
```

---

## Joining & Formatting Arrays

---

### String::ArrayToString

**Format an array for human-readable single-line printing with rich customization.**

```
String::ArrayToString = Func(
    Array( X ),                                 // The array to format
    String( Separator ) = ", ",                 // Delimiter between elements
    Double( Brackets )  = TRUE,                 // Include surrounding brackets
    Format              = String(),             // printf-style format or a lambda
    Double( Ignore Empty Elements ) := False,   // Omit empty/Null elements
    Array( Bookends ) := [ "[ ", " ]" ],        // Custom bracket characters
    Double( Max Line Length ) := Error Value,    // Wrap lines at this width
)
Returns( String() )
```

```slang
@String::ArrayToString( [ "ABC", "efg", "XYZ" ] );
// "[ ABC, efg, XYZ ]"

@String::ArrayToString( [ "ABC", "efg", "XYZ" ], " + ", True, "(%s)" );
// "[ (ABC) + (efg) + (XYZ) ]"

@String::ArrayToString( [ "ABC", "efg", "XYZ" ], " + ", False, "(%s)" );
// "(ABC) + (efg) + (XYZ)"

@String::ArrayToString( [ "", "ABC", Null, "efg", "", "XYZ", Null ], " + ", True, Ignore Empty Elements := True );
// "[ ABC + efg + XYZ ]"

@String::ArrayToString( [ "ABC", "efg", "XYZ" ], " + ", True, "(%s)", Max Line Length := 10 );
// "[ (ABC) +\n(efg) +\n(XYZ) ]"

// With a lambda formatter:
@String::ArrayToString( [ "ABC", "efg" ], " + ", True, \Elem -> Sprintf( "Size=%v", Size( Elem ) ) );
// "[ Size=3 + Size=3 ]"
```

---

### String::ArrayToString FormatCommandLineArgs

**Formatter for use with `ArrayToString` that wraps string elements in double quotes (for argv).**

```
String::ArrayToString FormatCommandLineArgs = Func(
    Any( e ),
)
Returns( String() )
```

```slang
@String::ArrayToString( [ 1, 2, "3 3 3" ], " ", False, String::ArrayToString FormatCommandLineArgs );
// 1 2 "3 3 3"
```

---

### String::StrJoin

**Join array elements with a glue string, with optional different glue for the last element.**

```
String::StrJoin = Func(
    String( Join ),                // Glue inserted between elements
    Array( Arr ),                  // Array of strings to join
    Double( Coerce ) := False,     // Convert non-strings to String first
    String( Last ) := Join,        // Different glue before the last element
)
Returns( String() )
```

```slang
@String::StrJoin( ", ", [ "Dirk", "Ossie", "Steve" ] );
// "Dirk, Ossie, Steve"

@String::StrJoin( ", ", [ "Dirk", "Ossie", "Steve" ], Last := " and " );
// "Dirk, Ossie and Steve"

@String::StrJoin( ", ", [ Date( "31dec99" ), 0, 3.14, "Hello World!" ], Coerce := True );
// "31dec99, 0, 3.14, Hello World!"
```

---

### String::List with Commas

**English-style list: "one, two, and three" with Oxford comma support.**

```
String::List with Commas = Func(
    Array( Elements ),
    String( Conjunction )   := "and",
    Double( Oxford Comma )  := True,
    Double( Coerce )        := False,
)
Returns( String() )
```

```slang
@String::List with Commas( [ "one", "two" ] );
// "one and two"

@String::List with Commas( [ "one", "two", "three" ] );
// "one, two, and three"

@String::List with Commas( [ "one", "two", "three" ], Conjunction := "or", Oxford Comma := False );
// "one, two or three"
```

---

### String::Join Array With Ellipsis

**Join an array, abbreviating with ellipsis if it exceeds a maximum element count.**

```
String::Join Array With Ellipsis = Func(
    Array( Array ),
    Double( Max Elements )               = 5,
    String( Glue )                      := ", ",
    String( Ellipsis )                  := "...",
    Double( Coerce Elements To String ) := True,
    Double( And N More )                := False,
)
Returns( String() )
```

```slang
@String::Join Array With Ellipsis( [ "a", "b", "c" ], 3 );
// "a, b, c"

@String::Join Array With Ellipsis( [ "a", "b", "c", "d" ], 3 );
// "a, b, c, ..."

@String::Join Array With Ellipsis( [ "a", "b", "c", "d" ], 3, And N More := True );
// "a, b, c and 1 more"
```

---

### String::Join Multiline

**Join an array of multi-line strings side by side (columnar layout).**

```
String::Join Multiline = Func(
    String( Glue ),                     // Glue between columns
    Array ( Parts ),                    // Array of multi-line strings
    String( Line Separator ) = "\n",    // Line separator
)
Returns( String() )
```

```slang
@String::Join Multiline( "\t", [
    "This is my\n1st paragraph\n",
    "Note that the\nfn works on\nirregular\nparagraphs.",
] );
// This is my      Note that the
// 1st paragraph   fn works on
//                 irregular
//                 paragraphs.
```

---

## Searching & Matching

---

### String::Count

**Count the number of (case-insensitive) occurrences of a substring.**

```
String::Count = Func(
    String( LongString ),
    String( SubString ),
)
Returns( Double() )
```

Overlapping matches are counted: `String::Count( "Abbabba", "Abba" )` returns `2`.

```slang
@String::Count( "aba    aba", "aba" );   // 2
@String::Count( "ababa", "ABA" );        // 2 (case-insensitive)
@String::Count( "hello", "xyz" );        // 0
```

---

### String::StrPosRev

**Find the last occurrence of a substring (reverse StrPos). Returns index or -1.**

```
String::StrPosRev = Func(
    String( String1 ),
    String( String2 ),
)
Returns( Double() )
```

```slang
@String::StrPosRev( "Every good boy deserves favour", "e" );  // 21
@String::StrPosRev( "Hello", "xyz" );                         // -1
```

---

### String::StrLastPos

**Find the last occurrence of a needle in a haystack. Returns index or -1.**

```
String::StrLastPos = Func(
    String( Haystack ),
    String( Needle ),
)
Returns( Double() )
```

```slang
@String::StrLastPos( "nnnn", "n" );  // 3
@String::StrLastPos( "This is quite a long string with several Ns in it", "n" );  // 45
```

---

### String::Pos Regex

**Find the first position matching a regular expression (like StrPos but for regex).**

```
String::Pos Regex = Func(
    String( Text ),
    RegEx( Search For ),
    Double( Initial ) = 0,      // Starting offset
)
Returns( Double() )
```

Returns `-1` if not found.

```slang
@String::Pos Regex( "ABC2ABC2ABC2", RegExP( "[0-9]" ) );      // 3
@String::Pos Regex( "ABC2ABC2ABC2", RegExP( "[0-9]" ), 4 );   // 7
@String::Pos Regex( "123456", RegExP( "[A-Z]" ) );             // -1
```

---

### String::Find Match

**Find the position of a matching closing bracket/delimiter, handling nesting.**

```
String::Find Match = Func(
    String( Str ),
    String( Open  ) := "(",
    String( Close ) := ")",
    Double( Start ) := 0,
)
Returns( Double() )
```

Returns `-1` if the open character is not found. Returns `Size( Str )` if close is not found.

```slang
@String::Find Match( "a(b(c)d)e", Open := "(", Close := ")" );           // 7
@String::Find Match( "(a,b),(c,d)", Open := "(", Close := ")" );          // 4
@String::Find Match( "(a,b),(c,d)", Open := "(", Close := ")", Start := 3 );  // 10
@String::Find Match( "a(b(c)d)e", Open := "[", Close := ")" );           // -1
```

---

### String::Search Strings

**Search for a term in an array of strings; returns prefix matches first, then contained matches.**

```
String::Search Strings = Func(
    String( Term ),                 // Search for this term
    Array( Strings ),               // Array of strings to search
    Double( Max Entries ) := 20,    // Maximum number of results
)
Returns( Array() )
```

Useful for autocomplete-style functionality.

---

## Prefix / Suffix / Contains

---

### String::Shared Prefix

**Find the common prefix shared by all strings in an array.**

```
String::Shared Prefix = Func(
    Array( Strings ),
)
Returns( String() )
```

Returns `""` if the array is empty, any string is empty, or no common prefix exists.

```slang
@String::Shared Prefix( [ "apple", "application", "apply" ] );  // "appl"
@String::Shared Prefix( [ "hello", "world" ] );                 // ""
```

---

### String::Remove Prefix

**Remove a prefix from a string. Returns the original string if the prefix is not present.**

```
String::Remove Prefix = Func(
    String( String ),
    String( Prefix ),
)
Returns( String() )
```

```slang
@String::Remove Prefix( "Goldman Sachs", "Goldman " );  // "Sachs"
@String::Remove Prefix( "Hello World", "Goodbye" );     // "Hello World" (unchanged)
```

---

### String::Remove Prefix Strict

**Remove a prefix, but throw an exception if the prefix is not present.**

```
String::Remove Prefix Strict = Func(
    String( String ),
    String( Prefix ),
)
Returns( String() )
```

```slang
@String::Remove Prefix Strict( "Goldman Sachs", "Goldman " );  // "Sachs"
@String::Remove Prefix Strict( "Hello World", "Goodbye" );     // THROWS
```

---

### String::Remove Suffix

**Remove a suffix from a string. Returns the original string if the suffix is not present.**

```
String::Remove Suffix = Func(
    String( String ),
    String( Suffix ),
)
Returns( String() )
```

```slang
@String::Remove Suffix( "example.txt", ".txt" );  // "example"
@String::Remove Suffix( "example.txt", ".pdf" );  // "example.txt" (unchanged)
```

---

### String::Remove Suffix Strict

**Remove a suffix, but throw an exception if the suffix is not present.**

```
String::Remove Suffix Strict = Func(
    String( String ),
    String( Suffix ),
)
Returns( String() )
```

```slang
@String::Remove Suffix Strict( "example.txt", ".txt" );  // "example"
@String::Remove Suffix Strict( "example.txt", ".pdf" );  // THROWS
```

---

### String::Begins With Any

**Test whether a string begins with any of a list of candidate prefixes.**

```
String::Begins With Any = Func(
    String( Str ),
    Array( Candidates ),
)
Returns( Double() )
```

Returns the **1-based index** of the matching candidate, or `False` (0) if none match. This lets you use it as both a boolean test and to identify which candidate matched (subtract 1 for the 0-based index).

```slang
@String::Begins With Any( "First Second", [ "first", "second", "third" ] );
// 1  (matched "first" -- case-insensitive)

!@String::Begins With Any( "Zero First", [ "first", "second" ] );
// True  (no match)
```

---

### String::Ends With Any

**Test whether a string ends with any of a list of candidate suffixes.**

```
String::Ends With Any = Func(
    String( Str ),
    Array( Candidates ),
)
Returns( Double() )
```

Same return convention as `Begins With Any`: 1-based index, or 0 for no match.

```slang
@String::Ends With Any( "End Test", [ "will", "test" ] );
// 2  (matched "test")
```

---

### String::Contains Any

**Test whether a string contains any of a list of candidate substrings.**

```
String::Contains Any = Func(
    String( Str ),
    Array( Candidates ),
)
Returns( Double() )
```

Returns `True` / `False` (unlike `Begins With Any`, does NOT return the index).

```slang
@String::Contains Any( "Contains Test", [ "not", "test" ] );  // True
@String::Contains Any( "Contains Test", [ "xyz", "abc" ] );   // False
```

---

### String::StrContains By Word

**Check if all words in SubString appear (as substrings) in String, in any order.**

```
String::StrContains By Word = Func(
    String( String ),
    String( SubString ),
)
Returns( Double() )
```

```slang
@String::StrContains By Word( "Ariel Alexander Amdur", "Alex Ari" );  // True
@String::StrContains By Word( "Ariel Alexander Amdur", "md lei" );    // False
```

---

### String::StrBegins By Word

**Check if all words in SubString are prefixes of words in String, in any order.**

```
String::StrBegins By Word = Func(
    String( String ),
    String( SubString ),
)
Returns( Double() )
```

```slang
@String::StrBegins By Word( "Ariel Alexander Amdur", "Al Ar" );  // True
@String::StrBegins By Word( "Ariel Alexander Amdur", "md" );     // False (substring, not prefix)
```

---

## Validation & Classification

---

### String::Is Digits

**Returns `True` if the string is non-empty and composed only of decimal digits (0-9).**

```
String::Is Digits = Func(
    String( Input Str ),
)
Returns( Double() )
```

No commas, minus signs, decimal points, or spaces allowed.

```slang
@String::Is Digits( "123" );    // True
@String::Is Digits( "-1" );     // False
@String::Is Digits( "1.2" );    // False
@String::Is Digits( "" );       // False
```

---

### String::Is Numeric

**Returns `True` if the string represents a valid number.**

```
String::Is Numeric = Func(
    String( Input Str ),
    Double( Allow Commas )        = FALSE,
    Double( Allow Percent )      := FALSE,
    Double( Allow Leading Plus ) := FALSE,
)
Returns( Double() )
```

```slang
@String::Is Numeric( "100" );                                       // True
@String::Is Numeric( "-100" );                                      // True
@String::Is Numeric( "  1  " );                                     // True
@String::Is Numeric( "1,234", /* Allow Commas */ True );             // True
@String::Is Numeric( "1,234", /* Allow Commas */ False );            // False
@String::Is Numeric( "100%", Allow Percent := True );                // True
@String::Is Numeric( "+100", Allow Leading Plus := True );           // True
```

---

### String::Is Percentage

**Returns `True` if the string is a percentage like "1.4 %".**

```
String::Is Percentage = Func(
    String( Input Str ),
)
Returns( Double() )
```

```slang
@String::Is Percentage( "1.4%" );           // True
@String::Is Percentage( "+1,234.56  %" );   // True
@String::Is Percentage( "100" );            // False
@String::Is Percentage( "%100" );           // False
```

---

### String::Is AlphaNumeric

**Returns `True` if the string contains only letters and digits (trimmed, spaces allowed at edges).**

```
String::Is AlphaNumeric = Func(
    String( Input Str ),
)
Returns( Double() )
```

```slang
@String::Is AlphaNumeric( "ABC123" );  // True
@String::Is AlphaNumeric( "abc" );     // True
@String::Is AlphaNumeric( " 1" );      // True  (leading space trimmed)
@String::Is AlphaNumeric( "1.2" );     // False
@String::Is AlphaNumeric( "" );        // False
```

---

### String::Is AlphaNumeric Upper

**Returns `True` if the string contains only uppercase letters and digits.**

```
String::Is AlphaNumeric Upper = Func(
    String( Input Str ),
)
Returns( Double() )
```

```slang
@String::Is AlphaNumeric Upper( "ABC123" );  // True
@String::Is AlphaNumeric Upper( "abc" );     // False
@String::Is AlphaNumeric Upper( "AbC" );     // False
```

---

### String::Is Text

**Returns `True` if the string contains only letters (no numbers, no punctuation).**

```
String::Is Text = Func(
    String( Input Str ),
)
Returns( Double() )
```

---

### String::Is Date

**Returns `True` if the string represents a date, using the standard date regex.**

```
String::Is Date = Func(
    String( Input Str ),
)
Returns( Double() )
```

```slang
@String::Is Date( "13Jul2013" );  // True
@String::Is Date( "01/12" );     // True
@String::Is Date( "19991225" );  // True
@String::Is Date( "hello" );     // False
@String::Is Date( "" );          // False
```

---

### String::Is Blank

**Returns `True` if the string is empty or contains only whitespace characters.**

```
String::Is Blank = Func(
    String( Input ),
)
Returns( Double() )
```

Whitespace characters include: space, `\r`, `\n`, `\t`, `\f`, `\v`.

```slang
@String::Is Blank( "  " );         // True
@String::Is Blank( "\r\n\t" );     // True
@String::Is Blank( " e" );         // False
@String::Is Blank( "" );           // True
```

---

## Case Conversion & Naming

---

### String::SplitOnCapitals

**Split a camelCase or PascalCase string into separate words.**

```
String::SplitOnCapitals = Func(
    String( Str ),
    Double( Handle Acronyms ) := False,
)
Returns( Array() )
```

```slang
@String::SplitOnCapitals( "HelloWorld" );
// [ "Hello", "World" ]

@String::SplitOnCapitals( "USD" );
// [ "U", "S", "D" ]

@String::SplitOnCapitals( "USD", Handle Acronyms := True );
// [ "USD" ]

@String::SplitOnCapitals( "USDExchangeRate", Handle Acronyms := True );
// [ "USD", "Exchange", "Rate" ]
```

---

### String::Camelize

**Convert "Hello world" to "HelloWorld" (or "helloWorld").**

```
String::Camelize = Func(
    String( Input String ),
    Double( Capitalize First Word ) := True,
)
Returns( String() )
```

```slang
@String::Camelize( "Hello world" );                              // "HelloWorld"
@String::Camelize( "Hello world", Capitalize First Word := False ); // "helloWorld"
```

---

### String::DeCamelize

**Convert "helloWorld" back to "hello world".**

```
String::DeCamelize = Func(
    String( Input String ),
    Double( Decapitalize First Word ) := True,
    Double( Retain Acronyms ) := False,
)
Returns( String() )
```

```slang
@String::DeCamelize( "helloWorld" );
// "hello world"

@String::DeCamelize( "helloWorld", Decapitalize First Word := False );
// "Hello World"

@String::DeCamelize( "SaveToDB", Decapitalize First Word := False, Retain Acronyms := True );
// "Save To DB"
```

---

### String::Start Case

**Map a camelCase string to "Start Case" format.**

```
String::Start Case = Func(
    String( St ),
)
Returns( String() )
```

```slang
@String::Start Case( "camelCase" );       // "Camel Case"
@String::Start Case( "GSCamelCase" );     // "GS Camel Case"
```

---

### String::CapUnderscoreToWords

**Convert `HELLO_WORLD` to `Hello World`.**

```
String::CapUnderscoreToWords = Func(
    String( A ),
)
Returns( String() )
```

---

### String::WordsToCapUnderscore

**Convert `hello world` to `HELLO_WORLD`.**

```
String::WordsToCapUnderscore = Func(
    String( A ),
)
Returns( String() )
```

```slang
@String::WordsToCapUnderscore( "a b c" );  // "A_B_C"
```

---

### String::WordsToJavaStyleVariableNames

**Convert `Hello World` to `helloWorld` (Java-style).**

```
String::WordsToJavaStyleVariableNames = Func(
    String( Variable ),
)
Returns( String() )
```

---

### String::UnderscoreToWords / String::WordsToUnderscore

**Convert between underscore-separated and space-separated forms (with `%` escaping for existing underscores).**

```slang
@String::UnderscoreToWords( "a_b%c" );  // "a b_c"
@String::WordsToUnderscore( "a b_c" );  // "a_b%c"
```

---

### String::Capitalize as Proper Noun

**Capitalize a string as a proper noun, with rules for articles, acronyms, etc.**

```
String::Capitalize as Proper Noun = Func(
    String( Str ),
    Array( Extra Uppercase Words ) := [],
)
Returns( String() )
```

Lowercases articles ("an", "and", "by", "the", etc.) except in initial position. Uppercases known acronyms ("IBM", "USD", "NYSE", etc.). You can add extra uppercase words via the optional argument.

```slang
@String::Capitalize as Proper Noun( "CVS CORPORATION" );
// "CVS Corporation"

@String::Capitalize as Proper Noun( "e.u. council of ministers" );
// "E.U. Council of Ministers"

@String::Capitalize as Proper Noun( "Extra", Extra Uppercase Words := [ "EXTRA" ] );
// "EXTRA"
```

---

### String::StrUpper Nth Char

**Uppercase the Nth character of every word in a string.**

```
String::StrUpper Nth Char = Func(
    String( Input ),
    String( Delim ) := " ",
    Double( Nth Char ) := 1,    // 1-based position
)
Returns( String() )
```

```slang
@String::StrUpper Nth Char( "hoW are you?", Delim := " ", Nth Char := 1 );
// "HoW Are You?"

@String::StrUpper Nth Char( "hoW|are|you?", Delim := "|", Nth Char := 2 );
// "hOW|aRe|yOu?"
```

---

## Wrapping & Indentation

---

### String::Wrap Around

**Wrap a string at a given column width, with word-chopping and alignment options.**

```
String::Wrap Around = Func(
    String( S ),
    Double( Width ),
    Double( Chop )                        = FALSE,
    Double( Preserve Width )             := FALSE,
    String( Alignment )                  := "Left",   // "Left", "Right", "Center"
    Double( Preserve Contiguous Spaces ) := False,
    String( Indent )                     := "",
    String( Join With )                  := "\n",
)
Returns( String() )
```

When `Chop = True`, wraps at word boundaries rather than mid-word.

---

### String::Wrap On Words

**Word-wrap text, with optional paragraph mode (blank-line-separated paragraphs).**

```
String::Wrap On Words = Func(
    String( Text ),
    Double( Width ),
    Double( Paragraph Mode ) := False,
)
Returns( String() )
```

---

### String::Indent

**Indent a string (or array of lines) with a prefix.**

```
String::Indent = Func(
    Var,                        // String or Array
    String( Prefix ) = "    ",
    String( Split ) := "\n",
    String( CR ) := "\n",
    String( First ) := Prefix,
)
Returns( String() )
```

```slang
@String::Indent( "dog\ncat\ncow", "> " );
// "> dog\n> cat\n> cow"

@String::Indent( [ "sheep", 2, Security( "EUR" ) ], "> " );
// "> sheep\n> 2\n> EUR"
```

---

### String::Nested Indent

**Recursively indent nested strings/arrays -- ideal for `Msg To String()` methods in Typed Structures.**

```
String::Nested Indent = Func(
    Var,                        // String or Array (nested arrays supported)
    String( Prefix ) = "  ",
    String( Split ) := "\n",
    String( CR )    := "\n",
    String( First ) := Prefix,
)
Returns( String() )
```

```slang
@String::Nested Indent( "abcd\n1234\nXYZH\nHello" );
// "  abcd\n  1234\n  XYZH\n  Hello"

// Nested indentation strips trailing newlines:
@String::Nested Indent( "abcd\n  level2 1234\n    level3 XYZH\nHello\n\n" );
// "  abcd\n    level2 1234\n      level3 XYZH\n  Hello"

// Works with arrays:
@String::Nested Indent( [ "abcd\n1234", "second1\nsecond2" ] );
// "  abcd\n  1234\n  second1\n  second2"
```

---

### String::DeTab

**Replace tabs with spaces, aligning to tab stops. Trims trailing whitespace from lines.**

```
String::DeTab = Func(
    String( Str ),
    Double( TabSize ) = 4,
)
Returns( String() )
```

This is *not* the same as naively replacing `\t` with spaces -- it aligns to tab-stop boundaries.

```slang
@String::DeTab( "\ta" );        // "    a"
@String::DeTab( "\ta", 2 );     // "  a"
@String::DeTab( "\tb\n\tc\td" );
// "    b\n    c   d"
```

---

## Truncation & Fitting

---

### String::Truncate

**Truncate a string to fit a maximum width, ending with an ellipsis if truncated.**

```
String::Truncate = Func(
    String( Str ),
    Double( Width ),
    String( Ellipsis ) := "...",
)
Returns( String() )
```

```slang
@String::Truncate( "Hello, Mum", 8 );   // "Hello..."
@String::Truncate( "Hello, Mum", 9 );   // "Hello,..."
@String::Truncate( "Hello, Mum", 10 );  // "Hello, Mum" (fits, not truncated)
@String::Truncate( "Hello, Mum", 11 );  // "Hello, Mum" (fits)
```

---

### String::Abbreviate

**Abbreviate a string to fit a maximum length (remove spaces first, then take initials).**

```
String::Abbreviate = Func(
    String( Full Text ),
    Double( Max Len ),
)
Returns( String() )
```

```slang
@String::Abbreviate( "cat  dog", 6 );   // "catdog" (just remove spaces)
@String::Abbreviate( "Cat Dog", 3 );    // "CD"     (initials, truncated)
@String::Abbreviate( "Cat Dog", 1 );    // "C"
```

---

### String::Fit To Length

**Intelligently shorten a multi-word string by removing vowels and trimming words evenly.**

```
String::Fit To Length = Func(
    String( Full String ),
    Double( Max Length ),
    Double( Spaces ) := True,   // If False, remove spaces between words
)
Returns( String() )
```

Preserves letter case. Prefers removing vowels over consonants and spaces over characters. Used in implied-name creation.

---

### String::Fit to Length with Mush

**Truncate then append a hash-derived suffix to preserve uniqueness.**

```
String::Fit to Length with Mush = Func(
    String( Full Text ),
    Double( Max Len ) = 31,
    Double( Mush Len ) = 4,
)
Returns( String() )
```

---

### String::Fit To Length By Split

**Split a string, then reassemble it to fit within a max length with custom separator/glue.**

```
String::Fit To Length By Split = Func(
    String( Str ),
    Double( Max Length ),
    String( Suffix ) := "",
    String( Prefix ) := "",
    String( Separator ) := "_",
    String( Glue ) := "_",
)
Returns( String() )
```

---

### String::Digest

**Mangle a sentence into a short file-name-safe or symbol-name-safe string.**

```
String::Digest = Func(
    String( Name ),
    Double( Total Length ) = 0,       // 0 = no limit
    Double( Length Per Word ) = 4,    // Max chars per word (0 = no limit)
    String( Pad ) = "",
)
Returns( String(), Double() )
```

---

## Numeric Conversion

---

### String::StringToDouble

**Convert a string with commas to a double (strips commas before casting).**

```
String::StringToDouble = Func(
    String( S ),
)
Returns( Double() )
```

```slang
@String::StringToDouble( "1,234,567.89" );  // 1234567.89
```

---

### String::Number To English

**Convert a number to its English-word representation.**

```
String::Number To English = Func(
    Double( Number ),
)
Returns( String() )
```

```slang
@String::Number To English( 0 );       // "zero"
@String::Number To English( 17 );      // "seventeen"
@String::Number To English( -1024 );   // "minus one thousand and twenty four"
@String::Number To English( 1000001 ); // "one million and one"
@String::Number To English( Error Value ); // "infinity"
```

---

### String::English To Number

**Convert English words back to a number (inverse of `Number To English`).**

```
String::English To Number = Func(
    String( English ),
)
Returns( Double() )
```

```slang
@String::English To Number( "seventeen" );  // 17
@String::English To Number( "minus one thousand and twenty four" );  // -1024
@String::English To Number( "infinity" );   // Error Value
```

---

### String::Cardinal To Ordinal

**Convert a cardinal number (or its English name) to an ordinal.**

```
String::Cardinal To Ordinal = Func(
    Any( Cardinal ),                      // Double (integer) or String
    Double( Use Number Format ) := False, // If True, return "1st" instead of "first"
)
Returns( String() )
```

```slang
@String::Cardinal To Ordinal( "one" );                                  // "first"
@String::Cardinal To Ordinal( 1 );                                      // "first"
@String::Cardinal To Ordinal( "one", Use Number Format := True );       // "1st"
@String::Cardinal To Ordinal( 2, Use Number Format := True );           // "2nd"
@String::Cardinal To Ordinal( 3, Use Number Format := True );           // "3rd"
@String::Cardinal To Ordinal( 17, Use Number Format := True );          // "17th"
@String::Cardinal To Ordinal( 111, Use Number Format := True );         // "111th"
```

---

## Base Encoding

---

### String::IntegerToBase36 / String::Base36ToInteger

**Convert between integers and base-36 strings (digits + uppercase letters).**

```
String::IntegerToBase36 = Func( Double( X ) ) Returns( String() )
String::Base36ToInteger = Func( String( X ) ) Returns( Double() )
```

Throws on negative input. Truncates fractional parts.

```slang
@String::IntegerToBase36( 1232 );  // "Y8"
@String::Base36ToInteger( "Y8" );  // 1232
@String::IntegerToBase36( 0 );     // "0"
@String::IntegerToBase36( 144 );   // "40"
@String::Base36ToInteger( "40" );  // 144
```

---

### String::IntegerToAlphaNumCode / String::AlphaNumCodeToInteger

**Compact 2-character codes for integers 0-1295 (00-99, then 0A-9Z, then A0-ZZ).**

```
String::IntegerToAlphaNumCode = Func( Double( X ) ) Returns( String() )
String::AlphaNumCodeToInteger = Func( String( In ) ) Returns( Double() )
```

Falls back to base-36 for numbers > 1295.

```slang
@String::IntegerToAlphaNumCode( 0 );       // "0"
@String::IntegerToAlphaNumCode( 101 );     // "0B"
@String::IntegerToAlphaNumCode( 1295 );    // "ZZ"
@String::IntegerToAlphaNumCode( 1296 );    // "100"
@String::IntegerToAlphaNumCode( 1008672 ); // "LMAO"

// Round-trip:
@String::AlphaNumCodeToInteger( @String::IntegerToAlphaNumCode( 101 ) );  // 101
```

---

### String::Encode Base36 / String::Decode Base36

**Encode/decode arbitrary ASCII strings to base-36-safe representation (case-insensitive, no special chars).**

```
String::Encode Base36 = Func( String( S ) ) Returns( String() )
String::Decode Base36 = Func( String( S ) ) Returns( String() )
```

Useful for file names. Uses `z` as escape character for non-alphanumeric bytes.

```slang
Encoded = @String::Encode Base36( "Hello World!" );
Decoded = @String::Decode Base36( Encoded );
// Decoded == "Hello World!"

// Round-trip is lossless:
@String::Decode Base36( @String::Encode Base36( S ) ) == S;  // always True
```

---

## String Similarity

---

### String::Convolution / String::Max Convolution

**Slide two strings across each other, counting character matches at each offset.**

```
String::Convolution = Func( String( String A ), String( String B ) ) Returns( Array() )
String::Max Convolution = Func( String( String A ), String( String B ) ) Returns( Double(), Null )
```

`Max Convolution` returns `Null` if both strings are length 0.

```slang
@String::Convolution( "Cat", "Dog Cat Cow" );
// [ 0, 0, 0, 0, 3, 0, 0, 0, 1, 0, 0 ]

@String::Max Convolution( "Cat", "Dog Cat Cow" );
// 3

@String::Max Convolution( "", "" );
// Null
```

---

### String::Levenshtein Distance

**Edit distance (insertions, deletions, substitutions) between two strings or arrays.**

```
String::Levenshtein Distance = Func(
    SubscriptableDatatype( S ),
    SubscriptableDatatype( T ),
    Double( Force Slang Impl ) := False,
)
Returns( Double() )
```

Uses the fast C++ built-in `LevenshteinDistance` for strings, falls back to a Slang implementation for arrays.

```slang
@String::Levenshtein Distance( "Hello World", "Hi there!" );  // 9
@String::Levenshtein Distance( "Apple", "Orange" );            // 5
@String::Levenshtein Distance( "aabc", "daabc" );             // 1
```

---

### String::Closest String

**From an array of candidates, return the one closest to a base string by Levenshtein distance.**

```
String::Closest String = Func(
    String( Base String ),
    Array( Candidates ),
    Slang( Tie Breaker ) = Slang(),   // Optional: Func( String1, String2 ) Returns( String() )
)
Returns( String() )
```

```slang
@String::Closest String( "apple", [ "ape", "apply", "orange" ] );
// "apply"
```

---

### String::Comparison Ratio

**Returns a similarity ratio (0 to 1) between two strings using sequence matching.**

```
String::Comparison Ratio = Func(
    String( Base String ),
    String( Comparison String ),
    Double( Use Quick Ratio ) := FalseBool,   // Quick upper-bound estimate
    Boolean( Ignore Case )    := FalseBool,
)
Returns( Double() )
```

A value > 0.6 generally means the strings are close. When `Use Quick Ratio` is `True`, the result may depend on argument order.

---

## Template / Variable Substitution

---

### String::FillIn From Structure

**Replace `%key%` placeholders in a template string with values from a Structure.**

```
String::FillIn From Structure = Func(
    String( S ),
    StringValueStructure( Map ),
    String( Brackets ) := "%%",         // Left & right delimiter characters
    Double( Resolve Nested ) := FALSE,  // Repeat substitution until stable
    Slang( Date Formatter ) := \dt -> String( dt ),
)
Returns( String() )
```

```slang
Data = "Test: %User%, Path: %Path%";
Map = Structure( "User", "courtan", "Path", "C:\\Foo" );
@String::FillIn From Structure( Data, Map );
// "Test: courtan, Path: C:\Foo"

// With dates and a custom formatter:
@String::FillIn From Structure( "/a/%Date%/test", {| Date := Date( "27Oct09" ) |}, Date Formatter := DateFns::YYYYMMDD );
// "/a/20091027/test"
```

---

### String::Extract To Structure

**Inverse of `FillIn From Structure`: extract values from a string given a template.**

```
String::Extract To Structure = Func(
    String( S ),
    String( Template ),
    String( Brackets ) := "%%",
)
Returns( Structure() )
```

```slang
S = "Test: courtan, Path: C:\\Foo, name: Antony Courtney";
Template = "Test: %User%, Path: %Path%, name: %Full Name%";
@String::Extract To Structure( S, Template );
// Structure( "User", "courtan", "Full Name", "Antony Courtney", "Path", "C:\\Foo" )
```

---

### String::Replace Variables

**Bash-like `${VAR}` substitution with backslash escaping.**

```
String::Replace Variables = Func(
    String( Input ),
    StringValueStructure( Replacements ),
    Array( Delimiters ) := [ "${", "}" ],
    String( Escape Char ) := "\\",
)
Returns( String() )
```

Throws if a referenced variable is not found in `Replacements`. Supports escaping: `\\${X}` produces literal `${X}`.

```slang
@String::Replace Variables( "${DATE} ${X}", {| Date := "[Today]", X := "Hello" |} );
// "[Today] Hello"
```

---

### String::Replace Word

**Replace occurrences of a find-string only when it appears as a whole word (not part of a larger word).**

```
String::Replace Word = Func(
    String( &Str ),             // Modified in place (pass by reference)
    String( FindStr ),
    String( ReplStr ),
    Double( Start ) := 0,              // Deprecated, do not use
    Double( Single Replace ) := False, // Replace only the first occurrence
)
Returns( Double() )
```

Returns `-1` if no replacement, otherwise the number of replacements (or position if `Single Replace`).

```slang
Str = "an band an apple banana";
@String::Replace Word( &Str, "an", "xxx" );
// Str == "xxx band xxx apple banana", returns 2
// Note: "band" and "banana" were NOT affected (word boundary check)
```

---

## Character-Level Utilities

---

### String::Reverse

**Reverse a string.**

```
String::Reverse = Func(
    String( Input ),
)
Returns( String() )
```

```slang
@String::Reverse( "abc" );   // "cba"
@String::Reverse( "" );      // ""
```

---

### String::Char Not In String

**Find a character (byte 1-255) that does not appear in the given string, or `Null` if all are present.**

```
String::Char Not In String = Func(
    String( S ),
)
Returns( String(), Null )
```

Useful for choosing a safe delimiter character when building split/replace operations.

---

### String::Condense Whitespace

**Replace runs of whitespace (spaces, tabs, newlines) with a single space, optionally trimming edges.**

```
String::Condense Whitespace = Func(
    Any( Input ),           // String or reference to a String
    Double( Trim ) := False,
)
Returns( String() )
```

```slang
@String::Condense Whitespace( "  hello  \t  goodbye\t\t\nNew line  " );
// " hello goodbye New line "

@String::Condense Whitespace( "  hello  \t  goodbye\t\t\nNew line  ", Trim := True );
// "hello goodbye New line"
```

---

### String::StrPad

**Pad a string to a target length with a given character, on either end.**

```
String::StrPad = Func(
    String( String ),
    Double( Padded String Length ),
    String( Padding Character ) := " ",  // Must be exactly 1 character
    Double( Pad End ) := True,           // True = pad right, False = pad left
)
Returns( String() )
```

```slang
@String::StrPad( "Hello", 10 );                              // "Hello     "
@String::StrPad( "Hello", 10, Pad End := False );             // "     Hello"
@String::StrPad( "Hello", 10, Padding Character := "-" );     // "Hello-----"
@String::StrPad( "Hello", 2 );                                // "Hello" (already fits)
```

---

### String::TrimZero

**Trim trailing zeros from a numeric string (optionally up to N zeros).**

```
String::TrimZero = Func(
    String( NumStr ),
    Double( Trim Up To ) := 0,   // 0 = trim all trailing zeros
)
Returns( String() )
```

Returns the original string unchanged if it is not numeric or has no decimal point.

```slang
@String::TrimZero( "98.125000" );      // "98.125"
@String::TrimZero( "98.125000", 2 );   // "98.1250"
@String::TrimZero( "12345" );          // "12345" (no decimal point -- unchanged)
@String::TrimZero( "abc.def" );        // "abc.def" (not numeric -- unchanged)
```

---

### String::Strip Leading Zeros

**Remove leading zeros from a zero-padded numeric string.**

```
String::Strip Leading Zeros = Func(
    String( NumStr ),
)
Returns( String() )
```

```slang
@String::Strip Leading Zeros( "007" );    // "7"
@String::Strip Leading Zeros( "  007 " ); // "7"  (also trims whitespace)
```

---

### String::Empty To Null

**Return `Null` if the string is empty or all-whitespace; otherwise return the original string.**

```
String::Empty To Null = Func(
    String( Input ),
)
Returns( String(), Null )
```

---

### String::Convert to Valid Chars

**Force a string to contain only valid characters for a given character set (ASCII, SecDb).**

```
String::Convert to Valid Chars = Func(
    String( String ),
    Double( Replace With Equivalent Chars ) := True,
    String( Default Replacement ) := "",
    String( Char Set ) := "ASCII",
)
Returns( String() )
```

When `Replace With Equivalent Chars` is `True`, attempts to replace accented/diacritical characters with ASCII equivalents. Supports Spanish, French, Italian, German, Dutch, Portuguese, Danish, Swedish, and Norwegian.

```slang
@String::Convert to Valid Chars( "Strasse" );    // "Strasse" (already ASCII)

// With replacement disabled:
@String::Convert to Valid Chars( "cafe", Replace With Equivalent Chars := False, Default Replacement := "?" );
// Non-ASCII characters replaced with "?"

// SecDb character set:
@String::Convert to Valid Chars( "!@#$%^&*()", Char Set := "SecDb" );
// "@#$%&*()"  (! and ^ are not valid in SecDb)
```

---

### String::NonPrintableCharExist

**Returns `True` if the string contains any non-printable characters (ASCII < 32 or > 126).**

```
String::NonPrintableCharExist = Func(
    String( Input ),
)
Returns( Double() )
```

Prefer the faster `ASCII::Contains NonPrintable Chars` when available.

```slang
@String::NonPrintableCharExist( "Hello\nWorld!" );  // True (\n is non-printable)
@String::NonPrintableCharExist( "Hello World!" );   // False
```

---

### String::ReplaceUnprintableChars

**Replace non-printable characters with a given replacement character.**

```
String::ReplaceUnprintableChars = Func(
    String( String ),
    String( Replacement ) = "?",   // Must be exactly 1 character
)
Returns( String() )
```

```slang
@String::ReplaceUnprintableChars( "Hello\nWorld!", "_" );  // "Hello_World!"
```

---

### String::RemoveUnprintableChars

**Remove all non-printable characters from a string.**

```
String::RemoveUnprintableChars = Func(
    String( String ),
)
Returns( String() )
```

```slang
@String::RemoveUnprintableChars( "Hello\nWorld! \n\tHow are you?" );
// "HelloWorld! How are you?"
```

---

### String::JSON Escape

**Escape a string for embedding in JSON (handles backslashes, quotes, control characters).**

```
String::JSON Escape = Func(
    String( S ),
)
Returns( String() )
```

Escapes `\`, `"`, `\b`, `\f`, `\n`, `\r`, `\t`, and non-printable characters as `\u00XX`.

---

## Multi-line / Columnar

---

### String::StrVerticalSlice

**Extract a vertical (columnar) slice from a multi-line string.**

```
String::StrVerticalSlice = Func(
    String( Str1 ),     // Input multi-line string
    Double( col1 ),     // Starting column (0-based)
    Double( col2 ),     // Ending column (inclusive; -1 for end of line)
)
Returns( String(), Double() )
```

```slang
Str = "apple\nbanana";
@String::StrVerticalSlice( Str, 0, 2 );   // "app\nban"
@String::StrVerticalSlice( Str, 0, 0 );   // "a\nb"
@String::StrVerticalSlice( Str, 2, -1 );  // "ple  \nnana "
```

---

### String::StrVerticalGlue

**Concatenate two multi-line strings side by side with a glue string.**

```
String::StrVerticalGlue = Func(
    String( Str1 ),
    String( Str2 ),
    String( GlueString ) = "",
)
Returns( String() )
```

```slang
@String::StrVerticalGlue( "apple\nbanana", "cherry\ndate", "=" );
// "apple =cherry\nbanana=date  "

@String::StrVerticalGlue( "apple\nbanana", "cherry\ndate", " ~~~ " );
// "apple  ~~~ cherry\nbanana ~~~ date  "
```

---

### String::Head Lines

**Return the first N lines of a string.**

```
String::Head Lines = Func(
    String( String ),
    Double( N ),
    String( SplitChar ) := "\n",
)
Returns( String() )
```

```slang
@String::Head Lines( "Apple\nBanana\nCherry\n", 1 );
// "Apple\n"

@String::Head Lines( "Apple\nBanana\nCherry\n", 2 );
// "Apple\nBanana\n"
```

---

### String::Tail Lines

**Return the last N lines of a string. If N < 0, skip the first |N| lines.**

```
String::Tail Lines = Func(
    String( String ),
    Double( N ),
    String( SplitChar ) := "\n",
)
Returns( String() )
```

```slang
@String::Tail Lines( "Apple\nBanana\nCherry\n", 1 );
// "Cherry\n"

@String::Tail Lines( "Apple\nBanana\nCherry\n", 2 );
// "Banana\nCherry\n"

@String::Tail Lines( "Apple\nBanana\nCherry\n", -1 );
// "Banana\nCherry\n"  (skip first line)
```

---

### String::Print onto End of Pad

**Overlay a string onto the right-hand end of a padding string.**

```
String::Print onto End of Pad = Func(
    Double( width ),
    String( what ),
    String( pad ),
)
Returns( String() )
```

```slang
@String::Print onto End of Pad( 12, "xxxx", "0123456789" );
// "01234567xxxx"
```

---

## Random String Generation

---

### String::Random Base10 / Random Base16 / Random Base32 / Random Base36 / Random Base64

**Generate cryptographically random strings of a given length in various bases.**

```
String::Random Base10 = Func( Double( Length ) ) Returns( String() )
String::Random Base16 = Func( Double( Length ) ) Returns( String() )
String::Random Base32 = Func( Double( Length ) ) Returns( String() )
String::Random Base36 = Func( Double( Length ) ) Returns( String() )
String::Random Base64 = Func( Double( Length ), Double( URL Safe ) := True ) Returns( String() )
```

Uses the operating system's true randomness source (`URandomDouble()`). All produce unbiased output.

```slang
@String::Random Base10( 8 );   // e.g. "47201938"
@String::Random Base16( 8 );   // e.g. "3FA1B20C"
@String::Random Base36( 6 );   // e.g. "K3M7QR"
```

---

## Packing / Serialization

---

### String::Length Prefix Pack / String::Length Prefix Unpack

**Pack an array of strings into a single string (and unpack it back) using length-prefix encoding.**

```
String::Length Prefix Pack = Func( Array( Unpacked Strings ) ) Returns( String() )
String::Length Prefix Unpack = Func( String( Packed Strings ) ) Returns( Array() )
```

Solves the in-band signaling problem: no need to choose a separator character that might appear in the data. As long as input strings do not contain embedded nulls, the output will not either.

```slang
Packed = @String::Length Prefix Pack( [ "hello", "world", "" ] );
@String::Length Prefix Unpack( Packed );
// [ "hello", "world", "" ]
```

---

### String::Unpack

**Break a fixed-width record string into a Structure according to a format table.**

```
String::Unpack = Func(
    Array( Format ),        // Table of [ Component, Format, Size [, Decimals ] ]
    String( Data ),
    Double( Check Size ) := False,
    Double( Trim ) := False,
)
Returns( Structure() )
```

```slang
Formats = TableInit( [
    [ "Component", "Format", "Size" ],
    [ "Name",      "String", 7 ],
    [ "ADate",     "Date",   7 ],
    [ Null,        "String", 6 ],   // skip 6 chars
    [ "Amount",    "Double", 6 ],
] );
Result = @String::Unpack( Formats, " Hello 02Feb10SkipMe123.23", Trim := _LEADING + _TRAILING );
// Result.Name == "Hello", Result.ADate == Date( "02Feb10" ), Result.Amount == 123.23
```

---

### String::Histogram

**Generate a text-based histogram chart from an array of values.**

```
String::Histogram = Func(
    Array( Values ),
    Double( Num Buckets ),
    Double( Bucket Precision ),
    String( Histogram Char ) := "*",
)
Returns( String() )
```

---

### String::ASCII XY Graph

**Plot an ASCII scatter/line graph from X and Y value arrays.**

```
String::ASCII XY Graph = Func(
    Array( X Values ),
    Array( Y Values ),
    Double( X Size ) := 80,
    Double( Y Size ) := 40,
    Double( Mark Points ) := True,
    Double( Show Axes ) := True,
    Double( Draw Lines ) := True,
)
Returns( String() )
```

---

## Sorting

---

### String::Natural Sort Order

**Comparator function for natural/human sort order (numbers sort numerically, not lexicographically).**

```
String::Natural Sort Order = Func(
    String( sa ),
    String( sb ),
)
Returns( Double() )
```

Returns `-1`, `0`, or `1`. Use as a comparator with `Sort()`.

```slang
@String::Natural Sort Order( "ANY PREFIX3", "ANY PREFIX3 AND SUFFIX" );  // -1
@String::Natural Sort Order( "ANY PREFIX3", "ANY PREFIX3" );             // 0
@String::Natural Sort Order( "ANY PREFIX3 AND SUFFIX", "ANY PREFIX10 AND SUFFIX" );  // -1

// To sort an array:
Arr = [ "rfc1.txt", "rfc2086.txt", "rfc822.txt" ];
Sort( Arr, String::Natural Sort Order );
// [ "rfc1.txt", "rfc822.txt", "rfc2086.txt" ]
```

---

# Part 2: Built-in Functions

These functions are available in every Slang script without any `Link()` statement.

---

## String Basics

---

### Size (on Strings)

**Get string length.**

```
Size( String ) => Double
```

```slang
Size( "Hello" );                         // 5
Size( "" );                              // 0
Size( "line1\nline2" );                  // 11 (newline is 1 character)
```

---

### String Indexing and Slicing

**Access individual characters (returns a length-1 string). Strings are 0-based.**

```slang
"hello"[ 0 ];    // "h"
"hello"[ 4 ];    // "o"

// Slice notation (0-based, inclusive on both ends):
"hello"[: 1, 3 :];   // "ell"
"hello"[: 0, 0 :];   // "h"
```

You can also **assign** to individual characters or slices:

```slang
S = "hello";
S[ 0 ] = "H";          // S is now "Hello"
S[: 0, 0 :] = "J";     // S is now "Jello"
```

---

### String (Constructor / Cast)

**Convert a value to its string representation.**

```
String( Value ) => String
```

```slang
String( 42 );                            // "42"
String( Date( "10Apr2025" ) );           // "10Apr25"
String( True );                          // "1"
```

---

## Searching

---

### StrPos

**Find the position of a substring.**

```
StrPos( String, SubString [, Start ] ) => Double
```

- Returns 0-based index of first occurrence of `SubString` in `String`.
- Returns `-1` if not found.
- Optional `Start` offset (default 0).

```slang
StrPos( "hello world", "world" );        // 6
StrPos( "abcabc", "bc", 2 );            // 4
StrPos( "hello", "xyz" );               // -1
```

---

### SubStr

**Extract a substring.**

```
SubStr( String, Start, End ) => String
SubStr( String, Start ) => String          // from Start to end of string
```

- `Start` and `End` are 0-based and **inclusive**.
- If only `Start` is given, returns from `Start` to the end of the string.

```slang
SubStr( "hello world", 0, 4 );          // "hello"
SubStr( "hello world", 6, 10 );         // "world"
SubStr( "hello world", 6 );             // "world"
```

---

### StrBegins

**Test if a string starts with a prefix (case-insensitive).**

```
StrBegins( String, Prefix ) => Double (True/False)
```

```slang
StrBegins( "Hello World", "Hello" );     // True
StrBegins( "Hello World", "hello" );     // True (case-insensitive)
StrBegins( "Hello World", "World" );     // False
```

---

### StrEnds

**Test if a string ends with a suffix (case-insensitive).**

```
StrEnds( String, SubString ) => Double (True/False)
```

```slang
StrEnds( "FooBar", "bAR" );                  // True (case-insensitive)
StrEnds( "FooBar", "Foo" );                  // False
```

---

### StrContains

**Test if a string contains a substring (case-insensitive).**

```
StrContains( String, SubString ) => Double (True/False)
```

```slang
StrContains( "Process Monitor", "process" );  // True
StrContains( "hello", "xyz" );                // False
```

---

## Replacing

---

### StrReplace

**Replace occurrences of a search string or regex.**

```
StrReplace( String, Search, Replace [, Flags ] ) => String
```

- `Search` can be a `String` or `RegExP`.
- Use `REPL_GLOBAL` flag to replace all occurrences (default: first only).
- Use `REPL_CASE` for case-sensitive replacement.

```slang
StrReplace( "foo bar foo", "foo", "baz", REPL_GLOBAL );  // "baz bar baz"
StrReplace( "a1b2c3", RegExP( "[0-9]" ), "", REPL_GLOBAL );  // "abc"
```

---

## Splitting & Joining

---

### StrSplit

**Split a string into an array by a single-character delimiter.**

```
StrSplit( String, Delimiter [, FilterEmpty ] ) => Array
```

- `FilterEmpty`: if `True`, excludes empty segments from the result.

```slang
StrSplit( "a.b.c", ".", False );         // [ "a", "b", "c" ]
StrSplit( "a,,b", ",", True );           // [ "a", "b" ]
StrSplit( "a,,b", ",", False );          // [ "a", "", "b" ]
```

---

### StrJoin

**Join an array into a string with a glue string.**

```
StrJoin( Glue, Array [, Coerce ] ) => String
```

```slang
StrJoin( ", ", [ "a", "b", "c" ] );      // "a, b, c"
StrJoin( "-", [ 1, 2, 3 ], True );       // "1-2-3"
```

---

### StrJustify

**Word-wrap a string into an array of lines, each no longer than a given width.**

```
StrJustify( String, Width ) => Array
```

---

## Case Conversion

---

### StrUpper

**Convert to upper case.**

```
StrUpper( String ) => String
```

```slang
StrUpper( "Hello World" );                   // "HELLO WORLD"
```

---

### StrLower

**Convert to lower case.**

```
StrLower( String ) => String
```

```slang
StrLower( "Hello World" );                   // "hello world"
```

---

### StrMixCase

**Capitalize the first character of each word.**

```
StrMixCase( String ) => String
```

```slang
StrMixCase( "hello world" );                 // "Hello World"
```

---

## Character Functions

---

### Asc

**Convert a character (first char of a string) to its ASCII code.**

```
Asc( String ) => Double
```

```slang
Asc( "A" );                                 // 65
Asc( "a" );                                 // 97
Asc( "\n" );                                // 10
```

---

### Chr

**Convert an ASCII code to a character (length-1 string).**

```
Chr( Code ) => String
```

```slang
Chr( 65 );                                   // "A"
Chr( 10 );                                   // newline
```

---

## Counting & Measuring

---

### StrChrCount

**Count occurrences of characters from a set within a string.**

```
StrChrCount( String, CharSet [, Start [, End]] ) => Double
```

```slang
StrChrCount( "FooBar", "oa", 2 );            // 2
StrChrCount( "aabbbcccc", "c" );             // 4
```

---

### StrHeight

**Return the number of lines in a multi-line string.**

```
StrHeight( String ) => Double
```

---

### StrWidth

**Return the maximum line width in a multi-line string.**

```
StrWidth( String ) => Double
```

---

## Comparison

---

### StrCmp

**Case-sensitive string comparison.**

```
StrCmp( String1, String2 ) => Double
```

Returns `< 0`, `0`, or `> 0` (like C's `strcmp`).

```slang
StrCmp( "abc", "ABC" );                      // > 0 (case-sensitive: lowercase > uppercase in ASCII)
StrCmp( "abc", "abc" );                      // 0
```

---

### StrICmp

**Case-insensitive string comparison.**

```
StrICmp( String1, String2 ) => Double
```

```slang
StrICmp( "abc", "ABC" );                     // 0
```

---

### StrNCmp

**Case-sensitive comparison of first N characters.**

```
StrNCmp( String1, String2, NumChars ) => Double
```

```slang
StrNCmp( "FooBar", "FooBaz", 4 );            // 0
```

---

### StrNICmp

**Case-insensitive comparison of first N characters.**

```
StrNICmp( String1, String2, NumChars ) => Double
```

```slang
StrNICmp( "FOOBAR", "foobaz", 4 );           // 0
```

---

### LevenshteinDistance

**Calculate the edit distance between two strings (built-in C++ implementation).**

```
LevenshteinDistance( String1, String2 ) => Double
```

```slang
LevenshteinDistance( "kitten", "sitting" );   // 3
```

---

## Formatting

---

### Sprintf

**Format values into a string (C-style).**

```
Sprintf( FormatString, Args... ) => String
```

Common specifiers: `%s` (string), `%d` (integer), `%f` (float), `%e` (scientific), `%v` (any value), `%%` (literal %).

```slang
Msg = Sprintf( "%s scored %d points (%.1f%%)", "Alice", 95, 95.0 );
// "Alice scored 95 points (95.0%)"
```

---

### Printf

**Print formatted output (C-style).**

```
Printf( FormatString, Args... ) => (void)
```

Same format specifiers as `Sprintf`, but writes directly to output.

```slang
Printf( "%-15s %8.2f\n", "Revenue", 1234.56 );
```

---

### Format

**Format a number with width, decimals, and flags.**

```
Format( NumericData, Width, Decimal, Flags ) => String
```

- `_Commas` flag adds thousand separators.

```slang
Format( 1234567.89, 15, 2, _Commas );   // "  1,234,567.89"
```

---

### StrRepeat

**Replicate a string N times.**

```
StrRepeat( String, Count ) => String
```

```slang
StrRepeat( "*-", 3 );                        // "*-*-*-"
StrRepeat( "=", 80 );                        // 80 equal signs
```

---

## Field Extraction

---

### StrField

**Extract a single space-separated field from a string.**

```
StrField( String [, FieldNum [, SplitChar]] ) => String
```

- `FieldNum`: 0-based index (default 0). Negative indexes from end.
- `SplitChar`: delimiter character (default: whitespace).

```slang
StrField( "Foo Bar" );                       // "Foo"
StrField( "Foo Bar", 1 );                    // "Bar"
StrField( "Foo Bar", -1 );                   // "Bar"
StrField( "Foo.Bar", 1, "." );              // "Bar"
```

---

### StrTranslate

**Translate characters: replace each character in `From` with the corresponding character in `To`.**

```
StrTranslate( String, From, To ) => String
```

Like Unix `tr`. `From` and `To` must be the same length.

---

### Trim

**Trim whitespace from a string.**

```
Trim( String, Flags ) => String
```

Flags: `_Leading`, `_Trailing`, or both with `_Leading | _Trailing` (or `_Leading + _Trailing`).

```slang
Trim( "  hello  ", _Leading | _Trailing );   // "hello"
Trim( "  hello  ", _Leading );               // "hello  "
Trim( "  hello  ", _Trailing );              // "  hello"
```

---

## Alignment

---

### Left

**Left-justify data within a fixed-width string.**

```
Left( Width, Data ) => String
```

```slang
Left( 20, "Hello" );                        // "Hello               "
```

---

### Right

**Right-justify data within a fixed-width string.**

```
Right( Width, Data ) => String
```

```slang
Right( 20, "Hello" );                       // "               Hello"
Right( 8, 3.14 );                            // "    3.14"
```

---

### Center

**Center data within a fixed-width string.**

```
Center( Width, Data ) => String
```

```slang
Center( 20, "Hello" );                      // "       Hello        "
```

---

## Regex

---

### RegExP

**Compile a regular expression pattern.**

```
RegExP( Pattern ) => RegExP
```

- Can also use `$~pattern~` inline syntax.

```slang
RE = RegExP( "[A-Z][a-z]+" );
RE = RegExP( $~\d{3}-\d{4}~ );
```

---

### RegMatch

**Match a compiled regex against a string.**

```
RegMatch( Pattern, String ) => Array
```

- Returns array of matches; empty array if no match.
- Element 0 is the full match; elements 1+ are capture groups.
- Use `Size()` of result as a boolean test.

```slang
Matches = RegMatch( RegExP( "([0-9]+)" ), "abc123" );
// Matches[ 0 ] = "123"

If( Size( RegMatch( RegExP( "^Error" ), Line ) ) )
{
    Print( "Line starts with Error\n" );
};
```

---

### RegMatchAll

**Find all matches of a regex in a string.**

```
RegMatchAll( Pattern, String ) => Array
```

---

### RegSub

**Regex-based substitution.**

```
RegSub( Pattern, String, Replacement [, Flags ] ) => String
```

---

## Encoding

---

### StrEscape

**Escape special characters in a string.**

```
StrEscape( String [, Mode] ) => String
```

---

### StrToHtml

**Encode a string for HTML/URL display.**

```
StrToHtml( String [, URLFlag] ) => String
```

---

### StrFromHtml

**Decode a URL-encoded string back to plain text.**

```
StrFromHtml( String ) => String
```

---

### StrFromBase64

**Decode a Base64 string.**

```
StrFromBase64( String ) => String
```

---

## Numeric Formatting

---

### InFormat

**Convert a formatted string back to a number.**

```
InFormat( String ) => Double
```

Understands `()`, `-`, `+`, `,`, `%`, `b`, `bp`, `m`, `k`, `eX`.

```slang
InFormat( "1,234.56" );                      // 1234.56
InFormat( "(100)" );                         // -100
InFormat( "50bp" );                          // 0.005
InFormat( "10k" );                           // 10000
InFormat( "2m" );                            // 2000000
```

---

### FormatDecimal

**Format an integer with optional comma separators and sign.**

```
FormatDecimal( Value [, Flags] ) => String
```

```slang
FormatDecimal( 9007199254740991, FORMAT_DECIMAL_PLUS | FORMAT_DECIMAL_COMMA );
// "+9,007,199,254,740,991"
```

---

### FormatDouble

**Format a double with optional exact representation.**

```
FormatDouble( Value [, Flags] ) => String
```

---

### FormatHex8 / FormatHex16 / FormatHex32 / FormatHex64

**Format an integer as a hexadecimal string.**

```slang
FormatHex8( 255 );                           // "0xff"
FormatHex32( -1 );                           // "0xffff'ffff"
```

---

## Miscellaneous Built-ins

---

### CvsPackText

**Pack a script expression for file output (converts leading spaces to tabs, trims trailing empty lines).**

```
CvsPackText( Expression ) => String
```

---

### Lex

**Tokenize a string into lexical tokens (for parsing).**

```
Lex( String ) => Array
```

Returns an array of structures with `.Token` (token type) and `.Value` fields.

---

## Concatenation Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `+` | Concatenate two strings | `"a" + "b"` => `"ab"` |
| `&=` | Append to string in place | `S &= " more"` |

---

## See Also

- [workingWithStrings.md](workingWithStrings.md) -- conceptual guide with patterns
- [examples.md](examples.md) -- practical recipes drawn from tests
- `.github/builtins.md` -- complete built-in function reference
