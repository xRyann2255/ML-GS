# String Functions -- Practical Examples

Recipes and patterns drawn from the `_LIB String Functions` test suite and real-world usage.
For the complete function reference see `commonFunctions.md`; for a conceptual walkthrough see `workingWithStrings.md`.

All library examples assume:

```slang
Link( "_LIB String Functions" );
```

---

## Table of Contents

1. [Fundamentals -- Indexing, Length, Comparison](#1-fundamentals)
2. [Splitting Strings](#2-splitting-strings)
3. [Joining Strings](#3-joining-strings)
4. [Searching and Finding](#4-searching-and-finding)
5. [Prefix, Suffix, and Contains Checks](#5-prefix-suffix-and-contains)
6. [Replacing and Substituting](#6-replacing-and-substituting)
7. [Validation and Classification](#7-validation-and-classification)
8. [Case Conversion and Naming Conventions](#8-case-conversion)
9. [Formatting and Padding](#9-formatting-and-padding)
10. [Wrapping, Indentation, and Multi-line](#10-wrapping-indentation)
11. [Truncation and Fitting](#11-truncation-and-fitting)
12. [Template Substitution](#12-template-substitution)
13. [Numeric Conversions](#13-numeric-conversions)
14. [Base Encoding](#14-base-encoding)
15. [String Similarity and Distance](#15-string-similarity)
16. [Character-Level Utilities](#16-character-level)
17. [Random String Generation](#17-random-strings)
18. [Serialization and Packing](#18-serialization)
19. [Common Patterns and Idioms](#19-common-patterns)

---

## 1. Fundamentals -- Indexing, Length, Comparison <a id="1-fundamentals"></a>

### String length

```slang
Size( "Hello" );       // 5
Size( "" );             // 0
Size( "line1\nline2" ); // 11 (the \n counts as 1 character)
```

### Character indexing (0-based)

Strings in Slang are **0-based**. Indexing returns a **length-1 string**, not a character type:

```slang
S = "Hello";
S[ 0 ];         // "H"
S[ 4 ];         // "o"
S[ Size( S ) - 1 ];  // "o" (last character)
```

### Slice notation

`Str[: start, end :]` extracts a range (0-based, inclusive on both ends):

```slang
"hello"[: 1, 3 :];   // "ell"
"hello"[: 0, 0 :];   // "h"
"abcdef"[: 2, 4 :];  // "cde"
```

### In-place modification

You can assign to individual characters or slices:

```slang
S = "hello";
S[ 0 ] = "H";          // S is now "Hello"
S[: 0, 0 :] = "J";     // S is now "Jello"
```

### Concatenation

```slang
Full = "Hello" + " " + "World";   // "Hello World"

// Append in place:
S = "Hello";
S &= ", World!";  // "Hello, World!"
```

### Comparison

Default `==` / `!=` is **case-insensitive**:

```slang
"hello" == "HELLO";    // True

// Case-sensitive comparison:
StrCmp( "hello", "HELLO" );   // > 0 (not equal)
StrCmp( "abc", "abc" );       // 0 (equal)

// Compare first N characters:
StrNCmp( "FooBar", "FooBaz", 4 );     // 0 (first 4 match)
StrNICmp( "FOOBAR", "foobaz", 4 );    // 0 (case-insensitive, first 4)
```

### Type checking

```slang
If( TypeOf( X ) == "String" )
{
    Print( "X is a string\n" );
};
```

### Casting to String

```slang
String( 42 );                // "42"
String( Date( "10Apr2025" ) ); // "10Apr25"
String( True );              // "1"
```

---

## 2. Splitting Strings <a id="2-splitting-strings"></a>

### Built-in StrSplit (single-character delimiter)

```slang
StrSplit( "a.b.c", ".", False );    // [ "a", "b", "c" ]
StrSplit( "a,,b", ",", True );      // [ "a", "b" ]        (empties filtered)
StrSplit( "a,,b", ",", False );     // [ "a", "", "b" ]    (empties kept)
```

### SplitMulti -- multiple delimiters at once

```slang
@String::SplitMulti( "abc  def.ghi", " ." );         // [ "abc", "", "def", "ghi" ]
@String::SplitMulti( "abc  def.ghi", " .", True );    // [ "abc", "def", "ghi" ]  (blanks filtered)
```

### StrSplitRecurse -- multiple delimiters (recursive)

```slang
@String::StrSplitRecurse( "a+b-c", "-+" );            // [ "a", "b", "c" ]
@String::StrSplitRecurse( "a+b-c-d+e", "-+" );        // [ "a", "b", "c", "d", "e" ]
```

### StrSplitOnWord -- multi-character word delimiter

```slang
@String::StrSplitOnWord( "SplitMyWord", "My" );
// [ "Split", "Word" ]

@String::StrSplitOnWord( "a,b,c,d", "," );
// [ "a", "b", "c", "d" ]

@String::StrSplitOnWord( "a==>b==>c==>d", "==>", Filter Blanks := True );
// [ "a", "b", "c", "d" ]

@String::StrSplitOnWord( "Test Test Tes", "Tes", True );
// [ "T", "T" ]  (trimmed, blanks removed)
```

### StrSplitDelims -- split with paired delimiters (brackets)

Will not split inside bracket pairs:

```slang
@String::StrSplitDelims(
    "First{A:On;B:Off};Second{C:True;D:False}", ";", "{", "}"
);
// [ "{A:On;B:Off}", "{C:True;D:False}" ]

// Parsing quoted fields:
@String::StrSplitDelims( "'foo' \t  2 bar", " \t", "'", "'", True, True );
// [ "foo", "2", "bar" ]
```

### StrSplitTrim -- split then trim

```slang
@String::StrSplitTrim( " xa x x x  b  x", "x", Skip Empty := True );
// [ "a", "b" ]

@String::StrSplitTrim( " xa x x x  b  x", "x", Skip Empty := False );
// [ "", "a", "", "b" ]
```

### SplitBySize -- fixed-width chunks

```slang
@String::SplitBySize( "foobarbaz", 3 );    // [ "foo", "bar", "baz" ]
@String::SplitBySize( "asdf", 3 );         // [ "asd", "f" ]
@String::SplitBySize( "asdf", 2 );         // [ "as", "df" ]
```

### Split Regex -- split on a regex pattern

```slang
@String::Split Regex( "The finex quick fine brown fine fox", RegExP( "fine" ) );
// [ "The ", "x quick ", " brown ", " fox" ]

// Include the matching delimiters:
@String::Split Regex( "The finex quick fine fox", RegExP( "fine" ), Include Matches := True );
// [ "The ", "fine", "x quick ", "fine", " fox" ]

// Trim and remove blanks:
@String::Split Regex( " HOLD abc HOLD xyz HOLD ", RegExP( "HOLD" ),
    Trim Elements := True, Remove Blank Elements := True );
// [ "abc", "xyz" ]
```

### Shell Split -- POSIX shell-style tokenization

```slang
@String::Shell Split( "bash -c \"echo hello\"" );
// [ "bash", "-c", "echo hello" ]

@String::Shell Split( "'hello world' foo" );
// [ "hello world", "foo" ]

// Unfinished quotes return an Error:
@String::Shell Split( "I'm broken" );
// Error: "Unfinished single-quoted string"
```

---

## 3. Joining Strings <a id="3-joining-strings"></a>

### StrJoin -- basic join

```slang
@String::StrJoin( ", ", [ "Dirk", "Ossie", "Steve" ] );
// "Dirk, Ossie, Steve"

// Different glue for the last element:
@String::StrJoin( ", ", [ "Dirk", "Ossie", "Steve" ], Last := " and " );
// "Dirk, Ossie and Steve"

// Join non-string types with coercion:
@String::StrJoin( ", ", [ Date( "31dec99" ), 0, 3.14, "Hello!" ], Coerce := True );
// "31dec99, 0, 3.14, Hello!"
```

### List with Commas -- English-style enumeration

```slang
@String::List with Commas( [ "one" ] );
// "one"

@String::List with Commas( [ "one", "two" ] );
// "one and two"

@String::List with Commas( [ "one", "two", "three" ] );
// "one, two, and three"  (Oxford comma by default)

@String::List with Commas( [ "one", "two", "three" ], Conjunction := "or", Oxford Comma := False );
// "one, two or three"
```

### ArrayToString -- rich formatting

```slang
// Default:
@String::ArrayToString( [ "ABC", "efg", "XYZ" ] );
// "[ ABC, efg, XYZ ]"

// Custom separator and printf format:
@String::ArrayToString( [ "ABC", "efg", "XYZ" ], " + ", True, "(%s)" );
// "[ (ABC) + (efg) + (XYZ) ]"

// Without brackets:
@String::ArrayToString( [ "ABC", "efg", "XYZ" ], " + ", False, "(%s)" );
// "(ABC) + (efg) + (XYZ)"

// Ignore empty/Null elements:
@String::ArrayToString( [ "", "ABC", Null, "efg", "", "XYZ", Null ], " + ", True,
    Ignore Empty Elements := True );
// "[ ABC + efg + XYZ ]"

// Nested arrays:
@String::ArrayToString( [ "element one", 1, 2.2, [ 3, [ 4, "five" ] ] ], " ", False,
    String::ArrayToString FormatCommandLineArgs );
// "\"element one\" 1 2.2 [ 3 [ 4 \"five\" ] ]"

// Custom bookends:
@String::ArrayToString( [ "a", "b" ], ",", True, Bookends := [ "{ ", " }" ] );
// "{ a, b }"

// With a lambda formatter:
@String::ArrayToString( [ "ABC", "efg" ], " + ", True,
    \Elem -> Sprintf( "Size=%v", Size( Elem ) ) );
// "[ Size=3 + Size=3 ]"
```

### Join Array With Ellipsis -- truncated lists

```slang
@String::Join Array With Ellipsis( [ "a", "b", "c" ], 3 );
// "a, b, c"

@String::Join Array With Ellipsis( [ "a", "b", "c", "d" ], 3 );
// "a, b, c, ..."

@String::Join Array With Ellipsis( [ "a", "b", "c", "d" ], 3, And N More := True );
// "a, b, c and 1 more"

@String::Join Array With Ellipsis( [ 1, 2, 3, 4, 5, 6, 7 ], Glue := ",", Ellipsis := " etc" );
// "1,2,3,4,5, etc"
```

### Join Multiline -- columnar layout

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

## 4. Searching and Finding <a id="4-searching-and-finding"></a>

### StrPos -- find position

```slang
StrPos( "hello world", "world" );        // 6
StrPos( "abcabc", "bc", 2 );            // 4 (search from offset 2)
StrPos( "hello", "xyz" );               // -1 (not found)
```

### StrPosRev -- find last occurrence

```slang
@String::StrPosRev( "Every good boy deserves favour", "e" );   // 21
@String::StrPosRev( "vry good boy dsrvs favour", "e" );        // -1
```

### StrLastPos

```slang
@String::StrLastPos( "nnnn", "n" );  // 3 (last 'n' is at position 3)
@String::StrLastPos( "This is quite a long string with several Ns in it", "N" );  // 45 (case-insensitive)
```

### Pos Regex -- find position by regex

```slang
@String::Pos Regex( "ABC2ABC2ABC2", RegExP( "[0-9]" ) );      // 3
@String::Pos Regex( "ABC2ABC2ABC2", RegExP( "[0-9]" ), 4 );   // 7
@String::Pos Regex( "123456", RegExP( "[A-Z]" ) );             // -1
```

### Count -- count substring occurrences

```slang
@String::Count( "aba    aba", "aba" );     // 2
@String::Count( "ababa", "ABA" );          // 2 (case-insensitive, overlapping matches)
@String::Count( "hello", "xyz" );          // 0
```

### Find Match -- bracket matching with nesting

```slang
@String::Find Match( "a(b(c)d)e", Open := "(", Close := ")" );
// 7 (position of the matching close paren for the first open paren)

@String::Find Match( "(a,b),(c,d)", Open := "(", Close := ")" );
// 4

@String::Find Match( "(a,b),(c,d)", Open := "(", Close := ")", Start := 3 );
// 10 (finds the second pair)
```

---

## 5. Prefix, Suffix, and Contains <a id="5-prefix-suffix-and-contains"></a>

### Built-in checks

```slang
StrBegins( "Hello World", "Hello" );     // True (case-insensitive)
StrEnds( "FooBar", "bAR" );             // True (case-insensitive)
StrContains( "Process Monitor", "process" );  // True
```

### Remove Prefix / Remove Suffix

```slang
@String::Remove Prefix( "Goldman Sachs", "Goldman " );   // "Sachs"
@String::Remove Prefix( "Hello World", "Goodbye" );      // "Hello World" (no change)

@String::Remove Suffix( "example.txt", ".txt" );          // "example"
@String::Remove Suffix( "example.txt", ".pdf" );          // "example.txt" (no change)

// Strict versions throw on mismatch:
@String::Remove Prefix Strict( "Hello World", "Goodbye" );  // THROWS!
@String::Remove Suffix Strict( "example.txt", ".pdf" );     // THROWS!
```

### Shared Prefix

```slang
@String::Shared Prefix( [ "abc", "abc.def", "abc.def.ghi" ] );
// "abc"

@String::Shared Prefix( [ "abc.xyz", "abc.def", "abc.mno", "abc.def.ghi" ] );
// "abc."

@String::Shared Prefix( [ "hello", "world" ] );
// ""
```

### Begins/Ends/Contains With Any

```slang
// Returns 1-based index of the matching candidate, or 0:
@String::Begins With Any( "First Second", [ "first", "second", "third" ] );
// 1 (matched "first")

@String::Ends With Any( "End Test", [ "will", "test" ] );
// 2 (matched "test")

@String::Contains Any( "Contains Test", [ "not", "test" ] );
// True

// Word-based matching:
@String::StrContains By Word( "Ariel Alexander Amdur", "Alex Ari" );
// True (each search word is a substring of the full string)

@String::StrBegins By Word( "Ariel Alexander Amdur", "Al Ar" );
// True (each search word is a prefix of a word in the full string)
```

---

## 6. Replacing and Substituting <a id="6-replacing-and-substituting"></a>

### StrReplace (built-in)

```slang
// Replace first occurrence:
StrReplace( "aabaa", "a", "x" );                           // "xabaa"

// Replace all:
StrReplace( "aabaa", "a", "x", REPL_GLOBAL );              // "xxbxx"

// With regex:
StrReplace( "abc123def", RegExP( "[0-9]+" ), "", REPL_GLOBAL );  // "abcdef"
```

### Replace Word -- whole-word-only replacement

```slang
Str = "an band an apple banana";
@String::Replace Word( &Str, "an", "xxx" );
// Str == "xxx band xxx apple banana"
// Note: "band" and "banana" are NOT modified (word boundary check)
// Returns 2 (number of replacements)
```

### Condense Whitespace

```slang
@String::Condense Whitespace( "  hello  \t  goodbye\t\t\nNew line  " );
// " hello goodbye New line "

@String::Condense Whitespace( "  hello  \t  goodbye  ", Trim := True );
// "hello goodbye"
```

---

## 7. Validation and Classification <a id="7-validation-and-classification"></a>

```slang
// Is Digits -- only 0-9, no sign, no decimal point
@String::Is Digits( "123" );     // True
@String::Is Digits( "-1" );      // False
@String::Is Digits( "" );        // False

// Is Numeric -- valid number (optionally with commas, %, leading +)
@String::Is Numeric( "100" );                                    // True
@String::Is Numeric( "-100" );                                   // True
@String::Is Numeric( "  1  " );                                  // True (trimmed)
@String::Is Numeric( "1,234", /* Allow Commas */ True );          // True
@String::Is Numeric( "100%", Allow Percent := True );             // True
@String::Is Numeric( "+100", Allow Leading Plus := True );        // True

// Is Percentage -- ends with %
@String::Is Percentage( "1.4%" );       // True
@String::Is Percentage( "+1,234  %" );  // True
@String::Is Percentage( "100" );        // False

// Is AlphaNumeric -- letters and digits only
@String::Is AlphaNumeric( "ABC123" );   // True
@String::Is AlphaNumeric( "1.2" );      // False

// Is AlphaNumeric Upper -- uppercase letters and digits only
@String::Is AlphaNumeric Upper( "ABC123" );  // True
@String::Is AlphaNumeric Upper( "abc" );     // False

// Is Text -- letters only
@String::Is Text( "teekatitoo" );         // True
@String::Is Text( "teekatitoo123" );      // False

// Is Date -- recognizable date string
@String::Is Date( "13Jul2013" );   // True
@String::Is Date( "19991225" );    // True
@String::Is Date( "hello" );      // False

// Is Blank -- empty or all whitespace
@String::Is Blank( "  \t\n" );    // True
@String::Is Blank( " e" );        // False
```

---

## 8. Case Conversion and Naming Conventions <a id="8-case-conversion"></a>

### Built-in case functions

```slang
StrUpper( "Hello World" );     // "HELLO WORLD"
StrLower( "Hello World" );     // "hello world"
StrMixCase( "hello world" );   // "Hello World"
```

### Camelize / DeCamelize

```slang
@String::Camelize( "Hello world" );                              // "HelloWorld"
@String::Camelize( "Hello world", Capitalize First Word := False ); // "helloWorld"

@String::DeCamelize( "helloWorld" );                             // "hello world"
@String::DeCamelize( "HiFriend", Decapitalize First Word := False );  // "Hi Friend"

// Handle acronyms:
@String::DeCamelize( "SaveToDB", Decapitalize First Word := False, Retain Acronyms := True );
// "Save To DB"
```

### SplitOnCapitals

```slang
@String::SplitOnCapitals( "HelloWorld" );
// [ "Hello", "World" ]

@String::SplitOnCapitals( "USDExchangeRate", Handle Acronyms := True );
// [ "USD", "Exchange", "Rate" ]
```

### Start Case

```slang
@String::Start Case( "camelCase" );          // "Camel Case"
@String::Start Case( "GSCamelCase" );        // "GS Camel Case"
```

### Capitalize as Proper Noun

```slang
@String::Capitalize as Proper Noun( "lDn irP floW raTe group" );
// "LDN IRP Flow Rate Group"

@String::Capitalize as Proper Noun( "bY sHoreHam-BY-sEa NOT of aUStrO-huNGary" );
// "By Shoreham-by-Sea Not of Austro-Hungary"

@String::Capitalize as Proper Noun( "CVS CORPORATION" );
// "CVS Corporation"

// Add custom uppercase words:
@String::Capitalize as Proper Noun( "Extra", Extra Uppercase Words := [ "EXTRA" ] );
// "EXTRA"
```

### CapUnderscoreToWords / WordsToCapUnderscore

```slang
@String::CapUnderscoreToWords( "HELLO_WORLD" );    // "Hello World"
@String::WordsToCapUnderscore( "a b c" );          // "A_B_C"
```

### WordsToJavaStyleVariableNames

```slang
@String::WordsToJavaStyleVariableNames( "this is a Variable name" );
// "thisIsAVariableName"
```

### UnderscoreToWords / WordsToUnderscore (round-trip safe)

```slang
Orig = "a b_c";
Underscored = @String::WordsToUnderscore( Orig );  // "a_b%c"
Back = @String::UnderscoreToWords( Underscored );   // "a b_c"
Assert( Orig == Back );
```

### StrUpper Nth Char

```slang
@String::StrUpper Nth Char( "hoW are you?", Delim := " ", Nth Char := 1 );
// "HoW Are You?"

@String::StrUpper Nth Char( "hoW|are|you?", Delim := "|", Nth Char := 2 );
// "hOW|aRe|yOu?"
```

---

## 9. Formatting and Padding <a id="9-formatting-and-padding"></a>

### Sprintf

```slang
Msg = Sprintf( "%s scored %d points (%.1f%%)", "Alice", 95, 95.0 );
// "Alice scored 95 points (95.0%)"

Formatted = Sprintf( "Price: %10.2f", 1234.5 );
// "Price:    1234.50"
```

### Format (numeric)

```slang
Format( 1234567.89, 15, 2, _Commas );    // "  1,234,567.89"
```

### StrPad

```slang
@String::StrPad( "Hello", 10 );                              // "Hello     "
@String::StrPad( "Hello", 10, Pad End := False );             // "     Hello"
@String::StrPad( "Hello", 10, Padding Character := "-" );     // "Hello-----"
@String::StrPad( "Hello", 2 );                                // "Hello" (already fits)
```

### Left / Right / Center alignment

```slang
Left( 20, "Hello" );     // "Hello               "
Right( 20, "Hello" );    // "               Hello"
Center( 20, "Hello" );   // "       Hello        "
Right( 8, 3.14 );        // "    3.14"
```

### StrRepeat

```slang
StrRepeat( "=", 40 );       // 40 equal signs: "========================================"
StrRepeat( "*-", 3 );       // "*-*-*-"
```

### TrimZero

```slang
@String::TrimZero( "98.125000" );       // "98.125"
@String::TrimZero( "96.00" );           // "96"
@String::TrimZero( "31.7800000", Trim Up To := 3 );  // "31.7800"
```

### Strip Leading Zeros

```slang
@String::Strip Leading Zeros( "007" );       // "7"
@String::Strip Leading Zeros( "  007 " );    // "7"
```

---

## 10. Wrapping, Indentation, and Multi-line <a id="10-wrapping-indentation"></a>

### Wrap Around

```slang
@String::Wrap Around( "abcdefg1234", 3 );
// "abc\ndef\ng12\n34"

@String::Wrap Around( "abcdefg1234", 5 );
// "abcde\nfg123\n4"

// With indent:
@String::Wrap Around( "abc de fg12 34", 4, True, Indent := "  " );
// "abc\n  de\n  fg12\n  34"
```

### Indent

```slang
@String::Indent( "dog\ncat\ncow", "> " );
// "> dog\n> cat\n> cow"

@String::Indent( [ "sheep", 2, Security( "EUR" ) ], "> " );
// "> sheep\n> 2\n> EUR"
```

### Nested Indent

```slang
@String::Nested Indent( "abcd\n1234\nXYZH\nHello" );
// "  abcd\n  1234\n  XYZH\n  Hello"

// Nested indentation accumulates:
@String::Nested Indent( "abcd\n  level2 1234\n    level3 XYZH\nHello\n\n" );
// "  abcd\n    level2 1234\n      level3 XYZH\n  Hello"

// Works with arrays (each element is a new section):
@String::Nested Indent( [ "abcd\n1234", "second1\nsecond2" ] );
// "  abcd\n  1234\n  second1\n  second2"
```

### DeTab

```slang
@String::DeTab( "\ta" );             // "    a"
@String::DeTab( "\ta", 2 );          // "  a"
@String::DeTab( "\tb\n\tc\td" );     // "    b\n    c   d"
@String::DeTab( "\tb\n\tcccc\td" );  // "    b\n    cccc    d"
```

### Head Lines / Tail Lines

```slang
Str = "Apple\nBanana\nCherry\n";

@String::Head Lines( Str, 1 );    // "Apple\n"
@String::Head Lines( Str, 2 );    // "Apple\nBanana\n"

@String::Tail Lines( Str, 1 );    // "Cherry\n"
@String::Tail Lines( Str, 2 );    // "Banana\nCherry\n"
@String::Tail Lines( Str, -1 );   // "Banana\nCherry\n"  (skip first line)
```

### StrVerticalSlice

```slang
Str = "apple\nbanana";

@String::StrVerticalSlice( Str, 0, 2 );    // "app\nban"
@String::StrVerticalSlice( Str, 0, 0 );    // "a\nb"
@String::StrVerticalSlice( Str, 2, -1 );   // "ple  \nnana "
```

### StrVerticalGlue

```slang
@String::StrVerticalGlue( "apple\nbanana", "cherry\ndate", "=" );
// "apple =cherry\nbanana=date  "

@String::StrVerticalGlue( "apple\nbanana", "cherry\ndate", " ~~~ " );
// "apple  ~~~ cherry\nbanana ~~~ date  "
```

### Print onto End of Pad

```slang
@String::Print onto End of Pad( 12, "xxxx", "0123456789" );
// "01234567xxxx"

@String::Print onto End of Pad( 8, "91005", "76095" );
// "76091005"
```

---

## 11. Truncation and Fitting <a id="11-truncation-and-fitting"></a>

### Truncate

```slang
@String::Truncate( "Hello, Mum", 8 );    // "Hello..."
@String::Truncate( "Hello, Mum", 9 );    // "Hello,..."
@String::Truncate( "Hello, Mum", 10 );   // "Hello, Mum" (fits, no truncation)
@String::Truncate( "Hello, Mum", 11 );   // "Hello, Mum"
```

### Abbreviate

```slang
@String::Abbreviate( "cat  dog", 6 );    // "catdog" (remove spaces)
@String::Abbreviate( "Cat Dog", 3 );     // "CD" (initials)
@String::Abbreviate( "Cat Dog", 1 );     // "C"
```

### Fit To Length -- intelligent shortening

Removes vowels and spaces evenly across words:

```slang
@String::Fit To Length( "Phase2 Exchange", 15 );    // "Phase2 Exchange" (fits)
@String::Fit To Length( "Phase2 Exchange", 12 );    // "Phas2 Exchng"
@String::Fit To Length( "Phase2 Exchange", 8 );     // "Phs2Exch"
@String::Fit To Length( "Phase2 Exchange", 4 );     // "PhEx"

// Without spaces:
@String::Fit To Length( "Phase2 Exchange", 10, Spaces := False );  // "Phas2Exchn"
```

### Digest

```slang
@String::Digest( "LDN IRP Flow Gilt Port" );
// "LDNIRPFlowGiltPort"
```

---

## 12. Template Substitution <a id="12-template-substitution"></a>

### FillIn From Structure

```slang
Data = "Test: %User%, Path: %Path%, name: %Full Name%";
Map = Structure( "User", "courtan", "Full Name", "Antony Courtney", "Path", "C:\\Foo" );
@String::FillIn From Structure( Data, Map );
// "Test: courtan, Path: C:\Foo, name: Antony Courtney"

// With { } brackets:
@String::FillIn From Structure( "Hello {User}!", Map, Brackets := "{}" );
// "Hello courtan!"

// With dates and a custom formatter:
@String::FillIn From Structure( "%Foo%|%Date%",
    {| Foo := "Test"; Date := Date( "27Oct09" ) |},
    Date Formatter := DateFns::YYYYMMDD );
// "Test|20091027"

// Nested resolution:
Nested Map = Structure( "Path", "{ROOT}\\Foo", "ROOT", "C:" );
@String::FillIn From Structure( "Dir: {Path}", Nested Map, Brackets := "{}", Resolve Nested := TRUE );
// "Dir: C:\Foo"
```

### Extract To Structure (inverse)

```slang
@String::Extract To Structure(
    "Test: courtan, Path: C:\\Foo, name: Antony Courtney",
    "Test: %User%, Path: %Path%, name: %Full Name%" );
// Structure( "User", "courtan", "Full Name", "Antony Courtney", "Path", "C:\\Foo" )
```

### Replace Variables (bash-style)

```slang
@String::Replace Variables( "${DATE} ${X}",
    {| Date := "[Today]", X := "Hello" |} );
// "[Today] Hello"

// Escaping with backslash:
@String::Replace Variables( "${DATE}4\\${DATE}\\\\${DATE}",
    {| Date := "[Today]" |} );
// "[Today]4${Date}\\[Today]"

// Throws on undefined variable:
@String::Replace Variables( "${UNDEFINED}",
    {| X := "1" |} );
// THROWS!
```

---

## 13. Numeric Conversions <a id="13-numeric-conversions"></a>

### StringToDouble

```slang
@String::StringToDouble( "1,000,000" );    // 1000000 (1e6)
@String::StringToDouble( "1e-4" );         // 0.0001
@String::StringToDouble( "+1234" );        // 1234
```

### Number To English / English To Number

```slang
@String::Number To English( 0 );           // "zero"
@String::Number To English( 17 );          // "seventeen"
@String::Number To English( -1024 );       // "minus one thousand and twenty four"
@String::Number To English( 1000001 );     // "one million and one"
@String::Number To English( Error Value ); // "infinity"

// Inverse:
@String::English To Number( "seventeen" );  // 17
@String::English To Number( "minus one thousand and twenty four" );  // -1024
@String::English To Number( "infinity" );   // Error Value

// Round-trip:
Number = 23023023023;
@String::English To Number( @String::Number To English( Number ) ) == Number;  // True
```

### Cardinal To Ordinal

```slang
@String::Cardinal To Ordinal( "one" );       // "first"
@String::Cardinal To Ordinal( 3 );           // "third"
@String::Cardinal To Ordinal( "twelve" );    // "twelfth"

// Numeric format:
@String::Cardinal To Ordinal( 1, Use Number Format := True );     // "1st"
@String::Cardinal To Ordinal( 2, Use Number Format := True );     // "2nd"
@String::Cardinal To Ordinal( 3, Use Number Format := True );     // "3rd"
@String::Cardinal To Ordinal( 17, Use Number Format := True );    // "17th"
@String::Cardinal To Ordinal( 111, Use Number Format := True );   // "111th"
```

### InFormat (built-in)

```slang
InFormat( "1,234.56" );   // 1234.56
InFormat( "(100)" );      // -100
InFormat( "50bp" );       // 0.005
InFormat( "10k" );        // 10000
InFormat( "2m" );         // 2000000
```

---

## 14. Base Encoding <a id="14-base-encoding"></a>

### IntegerToBase36 / Base36ToInteger

```slang
@String::IntegerToBase36( 1232 );   // "Y8"
@String::Base36ToInteger( "Y8" );   // 1232
@String::IntegerToBase36( 0 );      // "0"
@String::IntegerToBase36( 144 );    // "40"
@String::Base36ToInteger( "40" );   // 144

// Negative numbers throw:
@String::IntegerToBase36( -1 );     // THROWS
```

### IntegerToAlphaNumCode / AlphaNumCodeToInteger

```slang
@String::IntegerToAlphaNumCode( 0 );       // "0"
@String::IntegerToAlphaNumCode( 101 );     // "0B"
@String::IntegerToAlphaNumCode( 1295 );    // "ZZ"
@String::IntegerToAlphaNumCode( 1296 );    // "100" (falls back to base-36)
@String::IntegerToAlphaNumCode( 1008672 ); // "LMAO"

// Round-trip:
@String::AlphaNumCodeToInteger( @String::IntegerToAlphaNumCode( 101 ) );  // 101
```

### Encode Base36 / Decode Base36 (arbitrary strings)

```slang
Encoded = @String::Encode Base36( "Hello World!" );
Decoded = @String::Decode Base36( Encoded );
// Decoded == "Hello World!"

// Lossless round-trip for all ASCII including special chars:
S = " +&&*TG*h9n0\\sdf jowef\",8*-/+Hih";
@String::Decode Base36( @String::Encode Base36( S ) ) == S;  // True
```

---

## 15. String Similarity and Distance <a id="15-string-similarity"></a>

### Levenshtein Distance

```slang
// Built-in (fast C++ implementation):
LevenshteinDistance( "kitten", "sitting" );   // 3

// Library version (also works with arrays):
@String::Levenshtein Distance( "Hello World", "Hi there!" );  // 9
@String::Levenshtein Distance( "Apple", "Orange" );            // 5
@String::Levenshtein Distance( "aabc", "daabc" );             // 1
```

### Closest String

```slang
@String::Closest String( "apple", [ "ape", "apply", "orange" ] );
// "apply"

// With tie breaker:
@String::Closest String( "something", [ "a", "b", "c" ],
    \x, y -> If( y == "b" ) y : x );
// "b"
```

### Convolution / Max Convolution

```slang
@String::Convolution( "Cat", "Dog Cat Cow" );
// [ 0, 0, 0, 0, 3, 0, 0, 0, 1, 0, 0 ]

@String::Max Convolution( "Cat", "Dog Cat Cow" );
// 3

@String::Max Convolution( "", "" );
// Null
```

### Comparison Ratio

```slang
@String::Comparison Ratio( "Hello", "Hello" );              // 1.0
@String::Comparison Ratio( "Hello", "" );                   // 0.0
@String::Comparison Ratio( "Hello", "World" );              // 0.2
@String::Comparison Ratio( "HELLO", "hello", Ignore Case := TrueBool );  // 1.0
```

---

## 16. Character-Level Utilities <a id="16-character-level"></a>

### ASCII codes

```slang
Asc( "A" );    // 65
Asc( "a" );    // 97
Chr( 65 );     // "A"
Chr( 10 );     // "\n"
```

### Reverse

```slang
@String::Reverse( "abc" );   // "cba"
@String::Reverse( "" );      // ""
```

### Char Not In String

```slang
// Find a character that doesn't appear in the string (useful for choosing a safe delimiter):
Delim = @String::Char Not In String( My Data );
// Delim is a single character guaranteed not to appear in My Data
```

### NonPrintableCharExist / ReplaceUnprintableChars / RemoveUnprintableChars

```slang
@String::NonPrintableCharExist( "Hello\nWorld!" );       // True
@String::NonPrintableCharExist( "Hello World!" );        // False

@String::ReplaceUnprintableChars( "Hello\nWorld!", "_" );  // "Hello_World!"
@String::RemoveUnprintableChars( "Hello\nWorld!" );        // "HelloWorld!"
```

### Convert to Valid Chars

```slang
@String::Convert to Valid Chars( "financiere" );     // "financiere"
@String::Convert to Valid Chars( "garcon" );          // "garcon"
@String::Convert to Valid Chars( "CHATEAU" );         // "CHATEAU"

@String::Convert to Valid Chars( "!@#$%^&*()", Char Set := "SecDb" );
// "@#$%&*()"
```

### JSON Escape

```slang
@String::JSON Escape( "Hello\nWorld" );    // "Hello\\nWorld"
@String::JSON Escape( "Say \"hi\"" );      // "Say \\\"hi\\\""
```

### Empty To Null

```slang
@String::Empty To Null( "" );           // Null
@String::Empty To Null( "   " );        // Null
@String::Empty To Null( "Cave canem." );  // "Cave canem."
```

---

## 17. Random String Generation <a id="17-random-strings"></a>

```slang
@String::Random Base10( 8 );    // e.g. "47201938"
@String::Random Base16( 8 );    // e.g. "3FA1B20C"
@String::Random Base36( 6 );    // e.g. "K3M7QR"
@String::Random Base64( 12 );   // e.g. "aB3xY_z9Kp1m"
```

All functions use true OS randomness (`URandomDouble()`).

---

## 18. Serialization and Packing <a id="18-serialization"></a>

### Length Prefix Pack / Unpack

```slang
Packed = @String::Length Prefix Pack( [ "hello", "world", "" ] );
@String::Length Prefix Unpack( Packed );
// [ "hello", "world", "" ]

// Safe for strings containing any character:
Packed = @String::Length Prefix Pack( [ "a,b", "c|d", "" ] );
@String::Length Prefix Unpack( Packed );
// [ "a,b", "c|d", "" ]
```

### Unpack -- fixed-width record parsing

```slang
Formats = TableInit( [
    [ "Component", "Format", "Size" ],
    [ "Name",      "String", 7 ],
    [ "ADate",     "Date",   7 ],
    [ Null,        "String", 6 ],   // skip 6 characters
    [ "Amount",    "Double", 6 ],
] );

Result = @String::Unpack( Formats, " Hello 02Feb10SkipMe123.23",
    Trim := _LEADING + _TRAILING );
// Result.Name == "Hello"
// Result.ADate == Date( "02Feb10" )
// Result.Amount == 123.23
```

### Histogram

```slang
@String::Histogram( [ 1, 2, 3, 1, 2, 3, 3, 3 ], 2, 1 );
// "       1 : ***\n       2 : **\n       3 : ***\n"
```

---

## 19. Common Patterns and Idioms <a id="19-common-patterns"></a>

### Parse a delimited line into variables

```slang
Line = "John|Doe|42|Engineering";
Fields = StrSplit( Line, "|", False );
First Name  = Fields[ 0 ];             // "John"
Last Name   = Fields[ 1 ];             // "Doe"
Age         = Double( Fields[ 2 ] );   // 42
Department  = Fields[ 3 ];             // "Engineering"
```

### Build a string from parts (loop)

```slang
Names = [ "Alice", "Bob", "Carol" ];
Result = "";
ForEach( Name, Names )
{
    If( Size( Result ) > 0 )
    {
        Result &= ", ";
    };
    Result &= Name;
};
// Result = "Alice, Bob, Carol"

// Or use StrJoin:
@String::StrJoin( ", ", Names );   // "Alice, Bob, Carol"
```

### Validate a string pattern with regex

```slang
Is Valid Email = Func( String( Input ) )
Returns( Double() )
{
    Return( Size( RegMatch( RegExP( "^[^@]+@[^@]+\\.[^@]+$" ), Input ) ) > 0 );
};

Is Valid Email( "user@example.com" );    // True
Is Valid Email( "not-an-email" );        // False
```

### Extract all numbers from a string

```slang
Numbers = RegMatch( RegExP( "[0-9]+" ), "abc 123 def 456" );
// Numbers[ 0 ] = "123" (first match only with RegMatch)

// To get ALL matches, use a loop or StrReplace:
Clean = StrReplace( "Order#12345-X", RegExP( "[^0-9]" ), "", REPL_GLOBAL );
// "12345"
```

### Iterate over characters

```slang
S = "Hello";
For( I = 0; I < Size( S ); I++ )
{
    Print( S[ I ], " " );
};
// Output: H e l l o
```

### Safe delimiter for arbitrary data

```slang
// When you need to join/split strings that might contain any character:
Delim = @String::Char Not In String( All Data );
If( Delim != Null )
{
    Joined = @String::StrJoin( Delim, Data Array );
    Parts = StrSplit( Joined, Delim );
}
:
{
    // All 255 chars are present -- use Length Prefix Pack instead:
    Packed = @String::Length Prefix Pack( Data Array );
};
```

### Natural sort for filenames

```slang
Files = [ "rfc1.txt", "rfc2086.txt", "rfc822.txt" ];
Sort( Files, String::Natural Sort Order );
// [ "rfc1.txt", "rfc822.txt", "rfc2086.txt" ]
```

### Quick string report with vertical glue

```slang
Col1 = "Name\nAlice\nBob\nCarol";
Col2 = "Score\n95\n87\n92";
Report = @String::StrVerticalGlue( Col1, Col2, " | " );
// Name  | Score
// Alice | 95
// Bob   | 87
// Carol | 92
```

---

## See Also

- [commonFunctions.md](commonFunctions.md) -- complete function reference (signatures and parameters)
- [workingWithStrings.md](workingWithStrings.md) -- conceptual guide with patterns
- `.github/builtins.md` -- complete built-in function reference
