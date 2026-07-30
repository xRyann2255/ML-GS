# Working with Strings in Slang

A thorough conceptual guide to strings in Slang. Strings are arguably the most fundamental data type -- understanding their indexing, comparison semantics, slicing, and the rich built-in + library function ecosystem is essential for productive Slang programming.

For the complete function reference see [commonFunctions.md](commonFunctions.md).
For practical recipes see [examples.md](examples.md).

---

## Table of Contents

1. [String Fundamentals](#1-string-fundamentals)
2. [Creating Strings](#2-creating-strings)
3. [String Length](#3-string-length)
4. [Indexing and Character Access](#4-indexing-and-character-access)
5. [Slice Notation](#5-slice-notation)
6. [In-Place Modification](#6-in-place-modification)
7. [Concatenation and Appending](#7-concatenation-and-appending)
8. [Comparison Semantics](#8-comparison-semantics)
9. [Iterating Over Characters](#9-iterating-over-characters)
10. [Searching and Finding](#10-searching-and-finding)
11. [Extracting Substrings](#11-extracting-substrings)
12. [Splitting Strings](#12-splitting-strings)
13. [Replacing and Substituting](#13-replacing-and-substituting)
14. [Regular Expressions](#14-regular-expressions)
15. [Formatting and Printing](#15-formatting-and-printing)
16. [Trimming and Whitespace](#16-trimming-and-whitespace)
17. [Case Conversion](#17-case-conversion)
18. [Type Conversion (Casting)](#18-type-conversion-casting)
19. [Multiline Strings](#19-multiline-strings)
20. [Escape Characters](#20-escape-characters)
21. [Common Patterns and Idioms](#21-common-patterns-and-idioms)
22. [Gotchas and Pitfalls](#22-gotchas-and-pitfalls)

---

## 1. String Fundamentals

Strings in Slang are **sequences of characters** represented as a built-in data type. Key properties:

- Strings are enclosed in **double quotes**: `"Hello"`.
- They are **0-indexed**: the first character is at position 0.
- `Size( S )` returns the **length** (number of characters).
- Indexing a string returns a **length-1 string**, not a separate "character" type.
- Strings are **mutable**: you can assign to individual positions.
- The `==` operator is **case-insensitive** by default.
- Concatenation uses `+`; in-place append uses `&=`.

```slang
S = "Hello";
Size( S );          // 5
S[ 0 ];             // "H" (a length-1 string)
S[ 4 ];             // "o"
TypeOf( S );        // "String"
TypeOf( S[ 0 ] );   // "String" (not "Char" -- there is no Char type)
```

---

## 2. Creating Strings

### Double-Quoted Strings (Standard)

The most common way to create strings:

```slang
Greeting = "Hello, World!";
Empty = "";
With Escapes = "Line one\nLine two";
With Quotes = "He said, \"Hello!\"";
Tab Separated = "Col1\tCol2\tCol3";
```

### Dollar-Sign String Literals

When your string contains quotes, backslashes, or other special characters, dollar-sign strings let you pick a **custom delimiter** to avoid escaping:

```slang
// Syntax: $<delimiter><content><delimiter>
// The character immediately after $ becomes the delimiter

Path = $!C:\Users\Test\My "Special" Folder\notes.txt!;
Json = $|{"name": "Alice", "age": 30}|;
Html = $#<div class="container">Hello</div>#;
Regex = $~^[A-Z][a-z]+\d{2,4}$~;
```

### Multiline Dollar-Sign Strings

A common convention uses `$` itself as the delimiter (so the literal opens with `$$` and closes with a single `$`):

```slang
Sql Query = $$
    SELECT name, age
    FROM employees
    WHERE department = 'Engineering'
    ORDER BY name$;
```

> **Critical:** The closing delimiter is always a **single character** matching the one after the initial `$`. The form `$$text$$` is **invalid** -- the correct form is `$$text$`.

### Sprint (Concatenation Helper)

`Sprint()` concatenates all its arguments into a single string without any separator:

```slang
Msg = Sprint( "Error in ", Func Name, " at line ", Line Num );
// Equivalent to: "Error in " + Func Name + " at line " + String( Line Num )
```

`Sprint` is convenient when mixing types -- it automatically converts each argument to a string.

---

## 3. String Length

Use `Size()` to get the number of characters in a string:

```slang
Size( "Hello" );           // 5
Size( "" );                // 0
Size( "line1\nline2" );    // 11 (the \n is 1 character)
Size( "tab\there" );       // 8  (the \t is 1 character)
```

`Size()` is the **only** way to get string length. There is no `.Length` property or `Len()` function.

### Common length patterns

```slang
// Check if a string is empty
If( Size( S ) == 0 )
    Print( "Empty string\n" );

// Check if a string is non-empty
If( Size( S ) )
    Print( "Has content\n" );

// Get last character
Last = S[ Size( S ) - 1 ];

// Iterate from end
For( I = Size( S ) - 1; I >= 0; I-- )
    Print( S[ I ] );
```

---

## 4. Indexing and Character Access

Strings in Slang are **0-based**. Indexing returns a **length-1 string** (there is no separate character type):

```slang
S = "Hello";
S[ 0 ];             // "H"
S[ 1 ];             // "e"
S[ 4 ];             // "o"
S[ Size( S ) - 1 ]; // "o" (last character)
```

> **Important:** Negative indexing is **not supported**. To access the last character, use `S[ Size( S ) - 1 ]`.

### What indexing returns

Since there is no "Char" type in Slang, indexing always returns a `String`:

```slang
S = "ABC";
Ch = S[ 0 ];         // "A"
TypeOf( Ch );         // "String"
Size( Ch );           // 1

// This means comparisons work naturally:
If( S[ 0 ] == "A" )
    Print( "First char is A\n" );
```

### Character codes

To get the numeric (ASCII) code of a character, or to convert a code to a character:

```slang
// Character to ASCII code
Code = Asc( "A" );        // 65

// ASCII code to character
Ch = Chr( 65 );            // "A"

// Check if a character is a digit
If( Asc( Ch ) >= Asc( "0" ) && Asc( Ch ) <= Asc( "9" ) )
    Print( "It's a digit\n" );
```

---

## 5. Slice Notation

Slang strings support **slice notation** to extract a range of characters. The syntax is:

```
S[: start, end :]
```

Both `start` and `end` are **0-based** and **inclusive**:

```slang
S = "Hello, World!";
S[: 0, 4 :];        // "Hello"
S[: 7, 11 :];       // "World"
S[: 0, 0 :];        // "H" (single character)
```

### Slices vs SubStr

The slice notation `S[: start, end :]` is equivalent to `SubStr( S, start, end )`:

```slang
// These are equivalent:
S[: 2, 5 :];
SubStr( S, 2, 5 );
```

Use whichever reads more naturally in context. `SubStr` is often clearer when the indices come from variables.

### Slice with computed indices

```slang
S = "Hello, World!";

// Extract everything after the comma
Comma Pos = StrPos( S, "," );
After Comma = SubStr( S, Comma Pos + 2, Size( S ) - 1 );
// "World!"

// Extract the first N characters
First Five = S[: 0, 4 :];

// Extract the last N characters
N = 6;
Last N = SubStr( S, Size( S ) - N, Size( S ) - 1 );
// "orld!"  (wait, that's 5 -- remember end is inclusive!)
// For last 6: SubStr( S, Size( S ) - 6, Size( S ) - 1 ) => "World!"
```

---

## 6. In-Place Modification

Strings in Slang are **mutable**. You can assign to individual positions or slices:

```slang
S = "hello";
S[ 0 ] = "H";              // S is now "Hello"

S = "Jello";
S[: 0, 0 :] = "H";         // S is now "Hello"
```

> **Note:** When assigning to a single index, the replacement must be a length-1 string. When assigning to a slice, the replacement can be any length -- but be aware this modifies the string's length.

---

## 7. Concatenation and Appending

### The `+` operator

Creates a **new** string by joining two strings:

```slang
Full = "Hello" + ", " + "World!";  // "Hello, World!"
```

Non-string values are NOT automatically converted. Use `String()` or `Sprint()`:

```slang
// This will work because Sprint handles type conversion:
Msg = Sprint( "Count: ", 42 );

// Or explicitly cast:
Msg = "Count: " + String( 42 );
```

### The `&=` operator (append in place)

Appends to the existing string variable without creating a new intermediate string:

```slang
Result = "Hello";
Result &= ", ";
Result &= "World!";
// Result is now "Hello, World!"
```

`&=` is especially useful in loops:

```slang
Output = "";
For( I = 0; I < 5; I++ )
{
    If( I > 0 )
        Output &= ", ";
    Output &= String( I );
};
// Output = "0, 1, 2, 3, 4"
```

### Sprint (multi-argument concatenation)

`Sprint()` concatenates any number of arguments, auto-converting each to a string:

```slang
Sprint( "Name=", Name, " Age=", Age, " Date=", My Date );
```

### Sprintf (formatted concatenation)

When you need precise formatting, `Sprintf()` is the tool (see [Formatting and Printing](#15-formatting-and-printing)).

---

## 8. Comparison Semantics

### Default: case-insensitive

The `==` and `!=` operators for strings are **case-insensitive** by default:

```slang
"hello" == "HELLO";     // True
"Hello" == "hello";     // True
"abc" != "ABC";         // False (they ARE equal, case-insensitively)
```

### Case-sensitive comparison: StrCmp

To compare strings **case-sensitively**, use `StrCmp()`:

```slang
StrCmp( "Hello", "hello" );  // non-zero (they differ)
StrCmp( "Hello", "Hello" );  // 0 (equal)
StrCmp( "abc", "abd" );      // negative (abc < abd)
StrCmp( "abd", "abc" );      // positive (abd > abc)
```

`StrCmp` returns:
- `0` if the strings are equal (case-sensitive)
- Negative if the first string comes before the second
- Positive if the first string comes after the second

### Ordering operators

`<`, `>`, `<=`, `>=` compare strings lexicographically:

```slang
"apple" < "banana";    // True
"abc" < "abd";         // True
```

### StructureCase keys are case-sensitive

When strings are used as `StructureCase` keys, lookups are **case-sensitive**:

```slang
SC = StructureCase( "Hello", 1, "hello", 2 );
SC[ "Hello" ];    // 1
SC[ "hello" ];    // 2
SC[ "HELLO" ];    // error -- key not found
```

---

## 9. Iterating Over Characters

### Index-based loop (most common)

```slang
S = "Hello";
For( I = 0; I < Size( S ); I++ )
{
    Printf( "S[%d] = '%s'\n", I, S[ I ] );
};
// S[0] = 'H'
// S[1] = 'e'
// S[2] = 'l'
// S[3] = 'l'
// S[4] = 'o'
```

### Reverse iteration

```slang
S = "Hello";
For( I = Size( S ) - 1; I >= 0; I-- )
{
    Print( S[ I ] );
};
// olleH
```

### Building a new string character by character

```slang
S = "Hello, World!";
Vowels = "";
For( I = 0; I < Size( S ); I++ )
{
    Ch = StrUpper( S[ I ] );
    If( Ch == "A" || Ch == "E" || Ch == "I" || Ch == "O" || Ch == "U" )
        Vowels &= S[ I ];
};
// Vowels = "eoo"
```

### Counting characters

```slang
S = "Mississippi";
Count = 0;
For( I = 0; I < Size( S ); I++ )
{
    If( S[ I ] == "s" )
        Count++;
};
// Count = 4
```

> **Tip:** For counting substring occurrences, the library provides `@String::Count( S, Sub )` which is more efficient.

---

## 10. Searching and Finding

### StrPos -- find position of a substring

Returns the **0-based index** of the first occurrence, or **-1** if not found:

```slang
StrPos( "hello~world", "~" );           // 5
StrPos( "abcabc", "bc" );              // 1
StrPos( "abcabc", "bc", 2 );           // 4 (search from offset 2)
StrPos( "hello", "xyz" );              // -1 (not found)
```

### StrBegins -- check if string starts with a prefix

```slang
StrBegins( "Hello World", "Hello" );    // True
StrBegins( "Hello World", "World" );    // False
StrBegins( "", "" );                    // True
```

### StrEnds -- check if string ends with a suffix

```slang
StrEnds( "data.csv", ".csv" );          // True
StrEnds( "data.csv", ".txt" );          // False
```

### StrContains -- check if substring exists

Case-insensitive:

```slang
StrContains( "Process Monitor", "process" );  // True
StrContains( "Hello World", "xyz" );          // False
```

### Finding all occurrences

There is no built-in "find all" function, but you can loop with `StrPos`:

```slang
S = "abcabcabc";
Target = "abc";
Positions = [];
Pos = 0;
While( ( Pos = StrPos( S, Target, Pos ) ) >= 0 )
{
    Positions &= Pos;
    Pos += Size( Target );
};
// Positions = [ 0, 3, 6 ]
```

### Library search functions

With `Link( "_LIB String Functions" )`:

```slang
// Count occurrences of a substring
@String::Count( "Mississippi", "ss" );        // 2

// Find from the end
@String::StrLastPos( "abcabc", "bc" );        // 4

// Search an array of strings for one containing a substring
@String::Search Strings( [ "apple", "banana", "cherry" ], "nan" );
```

---

## 11. Extracting Substrings

### SubStr

Extracts from `Start` to `End` (both **inclusive**, **0-based**):

```slang
SubStr( "hello~world", 0, 4 );      // "hello"
SubStr( "hello~world", 6, 10 );     // "world"
SubStr( "hello~world", 0, 5 );      // "hello~" (index 5 is the ~)
```

### Slice notation

Equivalent to `SubStr`:

```slang
S = "hello~world";
S[: 0, 4 :];        // "hello"
S[: 6, 10 :];       // "world"
```

### Extract between delimiters

```slang
S = "Name: [John Doe], Age: 42";
Start = StrPos( S, "[" ) + 1;
End = StrPos( S, "]" ) - 1;
Name = SubStr( S, Start, End );      // "John Doe"
```

### First N / Last N characters

```slang
S = "Hello, World!";

// First 5
First Five = SubStr( S, 0, 4 );     // "Hello"

// Last 6
Last Six = SubStr( S, Size( S ) - 6, Size( S ) - 1 );  // "orld!"
// Wait -- let's count: Size is 13, 13-6=7, SubStr(S, 7, 12) = "World!" -- 6 chars. Correct.
Last Six = SubStr( S, Size( S ) - 6, Size( S ) - 1 );   // "World!"
```

---

## 12. Splitting Strings

### StrSplit -- split into an array

```slang
Parts = StrSplit( "a.b.c", ".", False );         // [ "a", "b", "c" ]
Parts = StrSplit( "one,two,,four", ",", True );  // [ "one", "two", "", "four" ]
Parts = StrSplit( "one,two,,four", ",", False ); // [ "one", "two", "four" ]
```

The third argument controls whether **empty strings** between consecutive delimiters are included.

### Split and process a delimited line

```slang
Line = "John|Doe|42|Engineering";
Fields = StrSplit( Line, "|", False );
First Name  = Fields[ 0 ];    // "John"
Last Name   = Fields[ 1 ];    // "Doe"
Age         = Double( Fields[ 2 ] );  // 42
Department  = Fields[ 3 ];    // "Engineering"
```

### Library splitting functions

With `Link( "_LIB String Functions" )`:

```slang
// Split on multiple single-character delimiters
@String::SplitMulti( "one.two,three;four", ".,;" );
// [ "one", "two", "three", "four" ]

// Split respecting delimiter pairs (e.g. brackets)
@String::StrSplitDelims( "a{x;y};b{z}", ";", "{", "}" );
// [ "{x;y}", "{z}" ]

// Split and trim whitespace from each element
@String::StrSplitTrim( "  a , b , c  ", "," );
// [ "a", "b", "c" ]

// Recursive split on multiple delimiter levels
@String::StrSplitRecurse( "a.b|c.d", [ "|", "." ] );
// [ [ "a", "b" ], [ "c", "d" ] ]
```

---

## 13. Replacing and Substituting

### StrReplace -- replace occurrences

```slang
// Replace first occurrence only (default)
StrReplace( "aabaa", "a", "x" );                         // "xabaa"

// Replace ALL occurrences
StrReplace( "aabaa", "a", "x", REPL_GLOBAL );            // "xxbxx"

// Remove a substring
StrReplace( "Hello World", " World", "" );                // "Hello"

// Replace with regex
StrReplace( "abc123def", RegExP( "[0-9]+" ), "", REPL_GLOBAL );  // "abcdef"
```

> **Key:** Without `REPL_GLOBAL`, only the **first** match is replaced. This is a common source of bugs.

### Library replacement functions

```slang
// Replace named variables in a template
Template = "Hello {{name}}, welcome to {{place}}!";
Values = Structure( "name", "Alice", "place", "Wonderland" );
@String::Replace Variables( Template, Values, "{{", "}}" );
// "Hello Alice, welcome to Wonderland!"

// Replace a whole word (not just a substring)
@String::Replace Word( "cat in a catalog", "cat", "dog" );
// "dog in a catalog" (only replaces whole-word match)
```

---

## 14. Regular Expressions

### Compiling a pattern

```slang
RE = RegExP( "[0-9]+" );

// Or using $~ syntax (avoids escaping backslashes):
RE = RegExP( $~[0-9]+~ );
RE = RegExP( $~^[A-Z][a-z]+\d{2,4}$~ );
```

### Matching

```slang
Matches = RegMatch( RegExP( "[0-9]+" ), "abc123def456" );
// Matches[ 0 ] = "123"

// Use Size() as a boolean test
If( Size( RegMatch( RegExP( "^[A-Z]" ), "Hello" ) ) )
    Print( "Starts with uppercase\n" );
```

### Replacing with regex

```slang
// Strip all whitespace
Clean = StrReplace( "  hello   world  ", RegExP( "\\s+" ), " ", REPL_GLOBAL );

// Extract digits only
Digits = StrReplace( "Order#12345-X", RegExP( "[^0-9]" ), "", REPL_GLOBAL );
// "12345"
```

### Library regex helpers

```slang
// Find position using regex
@String::Pos Regex( "abc123def", RegExP( "[0-9]+" ) );
// Returns structure with position info

// Split using regex
@String::Split Regex( "one123two456three", RegExP( "[0-9]+" ) );
// [ "one", "two", "three" ]
```

---

## 15. Formatting and Printing

### Sprintf -- formatted string creation

Works like C's `sprintf`. Returns the formatted string:

```slang
Msg = Sprintf( "%s is %d years old", "Alice", 30 );
// "Alice is 30 years old"

Formatted = Sprintf( "Price: %10.2f", 1234.5 );
// "Price:    1234.50"

Hex = Sprintf( "0x%04X", 255 );
// "0x00FF"
```

### Common format specifiers

| Specifier | Description | Example |
|-----------|-------------|---------|
| `%s` | String | `Sprintf( "%s", "hi" )` => `"hi"` |
| `%d` | Integer | `Sprintf( "%d", 42 )` => `"42"` |
| `%f` | Float | `Sprintf( "%.2f", 3.14 )` => `"3.14"` |
| `%e` | Scientific | `Sprintf( "%10.2e", 12345 )` => `"  1.23e+04"` |
| `%X` / `%x` | Hex | `Sprintf( "%X", 255 )` => `"FF"` |
| `%v` | Any value (auto) | `Sprintf( "%v", Curve )` |
| `%-Ns` | Left-justify in N chars | `Sprintf( "%-20s", "hi" )` |
| `%,Ns` | Number with commas | `Sprintf( "%,12.2s", 1234567 )` |
| `%@s` | Human-readable magnitude | `Sprintf( "%@s", 3100000 )` => `"3.1m"` |

### Printf -- print formatted to output

Same as `Sprintf` but writes directly to output instead of returning:

```slang
Printf( "Name: %-20s Age: %d\n", "Bob", 25 );
```

### Sprint -- simple concatenation to string

Concatenates all arguments into one string, converting each to a string:

```slang
Sprint( "Error: ", Error Code, " at ", Time() );
```

### Format -- numeric formatting

```slang
Format( 1234567.89, 15, 2, _Commas );
// "  1,234,567.89"
```

### Print -- output to console

```slang
Print( "Hello, World!\n" );
Print( "Name: ", Name, " Age: ", Age, "\n" );
```

`Print` does **not** add a newline automatically. Always include `"\n"` if you want one.

---

## 16. Trimming and Whitespace

### Trim -- remove leading and trailing whitespace

```slang
Trim( "  hello  " );          // "hello"
Trim( "\t hello \n" );        // "hello"
```

### Library whitespace functions

```slang
// Condense multiple whitespace to single spaces
@String::Condense Whitespace( "hello    world" );     // "hello world"

// Trim each line in a multiline string
@String::Trim Lines( "  line1  \n  line2  \n" );

// Convert tabs to spaces
@String::DeTab( "col1\tcol2", 8 );
```

---

## 17. Case Conversion

### Built-in

```slang
StrUpper( "hello" );    // "HELLO"
StrLower( "HELLO" );    // "hello"
```

### Library functions

```slang
// Capitalize first letter of each word
@String::Capitalize as Proper Noun( "hello world" );   // "Hello World"

// CamelCase to words
@String::DeCamelize( "myVariableName" );               // "my Variable Name"

// Words to CamelCase
@String::Camelize( "my variable name" );               // "myVariableName"

// Start Case
@String::Start Case( "hello_world" );                  // "Hello World"

// Uppercase the Nth character
@String::StrUpper Nth Char( "hello", 0 );              // "Hello"
```

---

## 18. Type Conversion (Casting)

### To String

Convert any type to its string representation:

```slang
String( 42 );                  // "42"
String( 3.14 );                // "3.14"
String( Date( "10Apr2025" ) ); // "10Apr25"
String( True );                // "1"
String( [ 1, 2, 3 ] );        // string representation of the array
```

### From String

Convert a string to other types:

```slang
Double( "42" );                // 42
Double( "3.14" );              // 3.14
Date( "10Apr2025" );           // Date value
Time( "10Apr2025 14:30:00" );  // Time value
```

### Type checking

```slang
X = "test";
TypeOf( X );                   // "String"
DataTypeOf( X );               // "String"

If( TypeOf( X ) == "String" )
    Print( "It's a string\n" );
```

---

## 19. Multiline Strings

### Creating multiline strings

The most common approach uses dollar-sign syntax:

```slang
Report = $$
Line 1: Summary
Line 2: Details
Line 3: Footer$;
```

Or with standard quotes and `\n`:

```slang
Report = "Line 1: Summary\nLine 2: Details\nLine 3: Footer";
```

### Splitting multiline strings into lines

```slang
Lines = StrSplit( Report, "\n", False );
// [ "Line 1: Summary", "Line 2: Details", "Line 3: Footer" ]
```

### Processing each line

```slang
Lines = StrSplit( Report, "\n", False );
ForEach( Line, Lines )
{
    Printf( ">> %s\n", Trim( Line ) );
};
```

### Library multiline functions

```slang
// Indent every line
@String::Indent( Report, "    " );

// Join two multiline strings side by side
@String::StrVerticalGlue( Col1, Col2, " | " );

// Get first N lines
@String::Head Lines( Report, 2 );

// Get last N lines
@String::Tail Lines( Report, 1 );
```

---

## 20. Escape Characters

Standard escape sequences in double-quoted strings:

| Sequence | Meaning |
|----------|---------|
| `\n` | Newline |
| `\t` | Tab |
| `\\` | Literal backslash |
| `\"` | Literal double quote |

```slang
Print( "Column1\tColumn2\n" );
Print( "She said \"Hello\"\n" );
Print( "Path: C:\\Users\\Test\n" );
```

Dollar-sign strings do **not** process escape sequences -- the content is taken literally:

```slang
S = $|Hello\nWorld|;
// S literally contains the characters \, n -- NOT a newline
Size( S );    // 12, not 11
```

---

## 21. Common Patterns and Idioms

### Build a comma-separated list

```slang
Names = [ "Alice", "Bob", "Carol" ];
Result = "";
ForEach( Name, Names )
{
    If( Size( Result ) > 0 )
        Result &= ", ";
    Result &= Name;
};
// "Alice, Bob, Carol"
```

Or with the library:

```slang
@String::StrJoin( ", ", Names );
// "Alice, Bob, Carol"
```

### Parse a delimited record

```slang
Line = "John|Doe|42|Engineering";
Fields = StrSplit( Line, "|", False );
First Name  = Fields[ 0 ];
Last Name   = Fields[ 1 ];
Age         = Double( Fields[ 2 ] );
Department  = Fields[ 3 ];
```

### Validate with regex

```slang
Is Valid Email = Size( RegMatch( RegExP( "^[^@]+@[^@]+\\.[^@]+$" ), Input ) ) > 0;
```

### Strip all non-alphanumeric characters

```slang
Clean = StrReplace( Input, RegExP( "[^A-Za-z0-9]" ), "", REPL_GLOBAL );
```

### Pad a string to a fixed width

```slang
// Right-pad with spaces (using Sprintf)
Padded = Sprintf( "%-20s", "Hello" );   // "Hello               "

// Left-pad with zeros (using library)
@String::StrPad( "42", 6, Padding Character := "0" );   // "000042"
```

### Check prefix/suffix and strip it

```slang
// Built-in check + manual strip
If( StrBegins( File, "report_" ) )
    Base Name = SubStr( File, 7, Size( File ) - 1 );

// Or with the library (cleaner)
Base Name = @String::Remove Prefix( File, "report_" );
File No Ext = @String::Remove Suffix( File, ".csv" );
```

### Count occurrences of a substring

```slang
@String::Count( "Mississippi", "ss" );   // 2
```

### Natural sort for filenames

```slang
Files = [ "rfc1.txt", "rfc2086.txt", "rfc822.txt" ];
Sort( Files, String::Natural Sort Order );
// [ "rfc1.txt", "rfc822.txt", "rfc2086.txt" ]
```

### Join an array with a limit and ellipsis

```slang
@String::Join Array With Ellipsis( [ "a", "b", "c", "d", "e" ], ", ", 3 );
// "a, b, c, ... (2 more)"
```

---

## 22. Gotchas and Pitfalls

### 1. `==` is case-insensitive

This is the single most common gotcha for new Slang programmers:

```slang
"ABC" == "abc";         // True!

// Use StrCmp for case-sensitive comparison:
StrCmp( "ABC", "abc" ); // non-zero (not equal)
```

### 2. StrReplace without REPL_GLOBAL only replaces the first match

```slang
StrReplace( "aaa", "a", "b" );                // "baa" (NOT "bbb"!)
StrReplace( "aaa", "a", "b", REPL_GLOBAL );   // "bbb"
```

### 3. SubStr end index is inclusive

Unlike many languages where the end index is exclusive, Slang's `SubStr` uses an **inclusive** end:

```slang
SubStr( "Hello", 0, 2 );   // "Hel" (3 characters, not 2)
```

### 4. No negative indexing

```slang
// This does NOT work:
// S[ -1 ];    // Error!

// Use this instead:
S[ Size( S ) - 1 ];
```

### 5. Dollar-sign strings don't process escapes

```slang
S = $|Hello\nWorld|;    // Contains literal \n, not a newline
S = "Hello\nWorld";     // Contains actual newline
```

### 6. String concatenation with non-strings

The `+` operator doesn't auto-convert. Use `Sprint()` or explicit `String()`:

```slang
// Might not work as expected depending on types:
// "Count: " + 42    -- be safe and cast

// Safe approaches:
Sprint( "Count: ", 42 );
"Count: " + String( 42 );
Sprintf( "Count: %d", 42 );
```

### 7. Empty string vs Null

An empty string `""` is a valid string with `Size()` of 0. `Null` is a different type entirely:

```slang
S = "";
Size( S );           // 0
IsError( S );        // False

S = Null;
TypeOf( S );         // not "String"
```

### 8. StrSplit delimiter is a single string, not individual characters

```slang
// This splits on the 2-character delimiter ".,"
StrSplit( "a.,b.,c", ".," );    // [ "a", "b", "c" ]

// NOT the same as splitting on "." OR ","
// For multi-delimiter splitting, use the library:
@String::SplitMulti( "a.b,c", ".," );   // [ "a", "b", "c" ]
```

---

## Quick Reference Table

| Task | Function / Operator | Example |
|------|---------------------|---------|
| Create | `"text"` or `$\|text\|` | `S = "hello";` |
| Length | `Size( S )` | `Size( "abc" )` => `3` |
| Index | `S[ n ]` | `"abc"[ 1 ]` => `"b"` |
| Slice | `S[: a, b :]` | `"abcde"[: 1, 3 :]` => `"bcd"` |
| Concatenate | `+`, `&=` | `"a" + "b"` => `"ab"` |
| Find position | `StrPos( S, Sub )` | Returns 0-based index or -1 |
| Starts with | `StrBegins( S, Prefix )` | Returns True/False |
| Ends with | `StrEnds( S, Suffix )` | Returns True/False |
| Contains | `StrContains( S, Sub )` | Case-insensitive |
| Extract | `SubStr( S, Start, End )` | Both inclusive, 0-based |
| Split | `StrSplit( S, Delim, InclEmpty )` | Returns Array |
| Replace | `StrReplace( S, Search, Repl )` | Add `REPL_GLOBAL` for all |
| Regex compile | `RegExP( Pattern )` | Returns compiled regex |
| Regex match | `RegMatch( RE, S )` | Returns Array of matches |
| Format | `Sprintf( Fmt, Args... )` | C-style format string |
| Uppercase | `StrUpper( S )` | `"hello"` => `"HELLO"` |
| Lowercase | `StrLower( S )` | `"HELLO"` => `"hello"` |
| Trim | `Trim( S )` | Remove leading/trailing whitespace |
| Cast to string | `String( Value )` | Convert any type |
| Compare (insensitive) | `==`, `!=` | Default behavior |
| Compare (sensitive) | `StrCmp( S1, S2 )` | Returns 0 if equal |
| Char to code | `Asc( Ch )` | `Asc( "A" )` => `65` |
| Code to char | `Chr( N )` | `Chr( 65 )` => `"A"` |

---

## See Also

- [commonFunctions.md](commonFunctions.md) -- complete function reference (Part 1: Library, Part 2: Built-in)
- [examples.md](examples.md) -- practical recipes drawn from tests
- `.github/builtins.md` -- complete built-in function reference
