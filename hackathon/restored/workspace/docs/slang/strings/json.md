# Working with JSON in Slang

## Overview

Slang has built-in support for serializing and deserializing JSON through two
functions:

| Function | Direction | Description |
|----------|-----------|-------------|
| `jsonify( value )` | Slang -> JSON | Converts a Slang data structure to a JSON string |
| `unjsonify( str )` | JSON -> Slang | Parses a JSON string into a Slang data structure |

Both functions are **built-in** -- no `Link()` is needed for basic usage.

However, if you use the date/time format constants (`JSON_DATE_FORMAT_ISO_8601`,
etc.), you must link the type definition that provides them:

```slang
Link( "_TYPE JSON String" );
```

---

## Quick Start

```slang
Link( "_TYPE JSON String" );

// Serialize a StructureCase to JSON
Data = StructureCase(
    "name",   "Alice";
    "age",    30;
    "active", True;
    "scores", [ 95, 87, 92 ];
);

Json String = jsonify( Data );
Print( Json String, "\n" );
// Output: {"name":"Alice","age":30,"active":true,"scores":[95,87,92]}

// Deserialize back to a StructureCase
Parsed = unjsonify( Json String );
Print( Parsed.name, "\n" );   // Alice
Print( Parsed.age, "\n" );    // 30
```

---

## jsonify -- Slang to JSON

### Signature

```
jsonify(
    value,                              // value to convert (Array, Structure, StructureCase, scalar)
    IntegerT( dateFormat )   := JSON_DATE_FORMAT_NONE,  // how to format Date values
    IntegerT( timeFormat )   := JSON_TIME_FORMAT_NONE,  // how to format Time values
    IntegerT( timePrec )     := 0,      // precision [0..6] for ISO 8601 time
    IntegerT( timestampPrec) := -2,     // precision [-2..9] for SDB::Timestamp
    Double( allowNanInf )    := false,  // allow NaN/Infinity (non-standard JSON)
    String( nanValue )       := "NaN",
    String( posInfinityValue) := "Infinity",
    String( negInfinityValue) := "-Infinity",
    Double( succinctDecimal ) := false  // shortest exact decimal for doubles
) Returns( String )
```

### Basic Usage

```slang
// StructureCase (becomes JSON object -- key order is preserved)
S = StructureCase( "x", 1; "y", 2 );
jsonify( S );     // {"x":1,"y":2}

// Array (becomes JSON array)
A = [ 1, "hello", True ];
jsonify( A );     // [1,"hello",true]

// Nested structures
Nested = StructureCase(
    "person", StructureCase( "name", "Bob"; "age", 25 );
    "tags",   [ "admin", "user" ];
);
jsonify( Nested );
// {"person":{"name":"Bob","age":25},"tags":["admin","user"]}
```

### Type Mapping

| Slang Type | JSON Type | Example |
|------------|-----------|---------|
| `String` | string | `"hello"` -> `"hello"` |
| `Double` / `Integer` | number | `3.14` -> `3.14` |
| `True` / `False` (Boolean) | boolean | `True` -> `true` |
| `Null` | null | `Null` -> `null` |
| `Array` | array | `[1, 2]` -> `[1,2]` |
| `Structure` / `StructureCase` | object | `{\ "a" := 1 \}` -> `{"a":1}` |

> **Important:** `Date` and `Time` values require explicit format constants
> (see below). Without them, dates and times will **not** convert properly.

### Handling Dates and Times

By default, `jsonify` does **not** know how to format `Date()` and `Time()` values.
You must pass the appropriate format constants, which are defined in
`_TYPE JSON String`:

```slang
Link( "_TYPE JSON String" );

Data = StructureCase(
    "trade_date",  Date( "19Jan2026" );
    "timestamp",   DateTime( Today() );
    "price",       100.50;
);

// Without date/time format -- dates will NOT serialize correctly
Bad = jsonify( Data );

// With ISO 8601 formats -- correct
Good = jsonify( Data,
    JSON_DATE_FORMAT_ISO_8601,
    JSON_TIME_FORMAT_ISO_8601
);
Print( Good, "\n" );
// {"trade_date":"2026-01-19","timestamp":"2026-02-18T00:00:00","price":100.5}
```

#### Available Format Constants

| Constant | Value | Effect |
|----------|-------|--------|
| `JSON_DATE_FORMAT_NONE` | 0 | No date conversion (default) |
| `JSON_DATE_FORMAT_ISO_8601` | 1 | Dates as `"YYYY-MM-DD"` |
| `JSON_TIME_FORMAT_NONE` | 0 | No time conversion (default) |
| `JSON_TIME_FORMAT_ISO_8601` | 1 | Times as `"YYYY-MM-DDTHH:MM:SS"` |

You can use named parameters for clarity:

```slang
jsonify( Data, dateFormat := JSON_DATE_FORMAT_ISO_8601, timeFormat := JSON_TIME_FORMAT_ISO_8601 );
```

Or positional (the date format is the 2nd arg, time format is the 3rd):

```slang
jsonify( Data, JSON_DATE_FORMAT_ISO_8601, JSON_TIME_FORMAT_ISO_8601 );
```

### Handling NaN and Infinity

Standard JSON does not permit `NaN` or `Infinity`. By default, `jsonify` will
throw an error if it encounters these values. To allow them:

```slang
Data = StructureCase( "value", 0.0 / 0.0 );  // NaN

// This would throw by default; enable with:
jsonify( Data, allowNanInf := true );
// {"value":NaN}
```

### Succinct Decimal Output

The `succinctDecimal` flag outputs the shortest decimal string that exactly
represents each double-precision value. Useful for minimizing JSON size:

```slang
jsonify( StructureCase( "pi", 3.14159265358979 ), succinctDecimal := true );
```

---

## unjsonify -- JSON to Slang

### Signature

```
unjsonify(
    String( input_string ),                  // the JSON string
    Double( unwrapBooleanAsBoolean ) := false // true = JSON true/false -> Slang Boolean
) Returns( DtValueVar )                      // Array or StructureCase
```

### Basic Usage

```slang
// JSON object -> StructureCase
Result = unjsonify( $|{"name":"Alice","age":30}| );
Print( Result.name, "\n" );   // Alice
Print( Result.age, "\n" );    // 30

// JSON array -> Array
Arr = unjsonify( "[1, 2, 3]" );
Print( Arr, "\n" );           // [1, 2, 3]

// Nested
Nested = unjsonify( $|{"data":{"items":[1,2,3]}}| );
Print( Nested.data.items, "\n" );  // [1, 2, 3]
```

### Type Mapping

| JSON Type | Slang Type |
|-----------|------------|
| string | `String` |
| number (integer) | `Double` |
| number (float) | `Double` |
| boolean (`true`/`false`) | `Double` (1/0) by default, or `Boolean` if `unwrapBooleanAsBoolean := true` |
| null | `Null` |
| array | `Array` |
| object | `StructureCase` |

### Boolean Handling

By default, JSON `true`/`false` become Slang `1`/`0` (doubles). If you
need actual Slang `Boolean` values:

```slang
Result = unjsonify( $|{"active": true}|, unwrapBooleanAsBoolean := true );
// Result.active is now Boolean True, not Double 1
```

---

## Writing JSON Inline (Dollar-Sign Strings)

For embedding JSON literals directly in Slang code, use dollar-sign strings
to avoid quote escaping:

```slang
// Use $| ... | for single-line JSON
Config = unjsonify( $|{"host":"localhost","port":8080}| );

// Use $$ ... $ for multi-line JSON (most common pattern)
Request = unjsonify( $$
{
    "functions": [ "GetPrice", "GetVolume" ],
    "arguments": [
        { "ticker": "AAPL", "date": "2026-01-15" },
        { "ticker": "AAPL", "date": "2026-01-15" }
    ],
    "context": { "database": "marketdata" }
}
$ );

Print( Request.functions, "\n" );  // [ "GetPrice", "GetVolume" ]
```

> **Reminder:** `$$` opens the string, a single `$` closes it. The closing `$`
> must be the **only** thing on the line (or followed by `;`).

---

## Roundtrip Example

A complete example demonstrating serialization, deserialization, and verification:

```slang
Link( "_TYPE JSON String" );

// Build a test structure with various types
Original = StructureCase(
    "string",   "abcd";
    "boolean",  True;
    "double1",  1.1;
    "double2",  2E-5;
    "array1",   [ 1, 2, 3 ];
    "array2",   [ "a", "b", "c" ];
);

// Serialize to JSON
Json = jsonify( Original );
Printf( "JSON: %s\n", Json );

// Deserialize back
Restored = unjsonify( Json );

// Verify roundtrip
Print( "Match: ", Original == Restored, "\n" );  // 1 (True)
```

### Roundtrip with Dates

When dates and times are involved, you **must** provide the format constants
on serialization. Note that `unjsonify` returns date strings as plain strings --
you will need to parse them back to `Date()` / `Time()` manually if needed:

```slang
Link( "_TYPE JSON String" );

Original = StructureCase(
    "trade_date", Date( "19Jan2026" );
    "price",      100.50;
);

Json = jsonify( Original, JSON_DATE_FORMAT_ISO_8601, JSON_TIME_FORMAT_ISO_8601 );
Print( Json, "\n" );
// {"trade_date":"2026-01-19","price":100.5}

Parsed = unjsonify( Json );
Print( Parsed.trade_date, "\n" );  // "2026-01-19" (a String, not a Date)
// To get a Date back:
Trade Date = Date( Parsed.trade_date );
```

---

## Real-World Pattern: REST API Payloads

A common use of `jsonify`/`unjsonify` is constructing and parsing REST API
request/response bodies:

```slang
Link( "_TYPE JSON String" );

// Build request payload as a StructureCase
Payload = StructureCase(
    "functions", [ "GetTradeDetails", "GetValue" ];
    "arguments", [
        StructureCase(
            "Book Tag", "GSIL Profit Center";
            "Group",    "RegTest Group";
        ),
        StructureCase(
            "VT",       "Data Addenda";
            "Security", "VOD.L";
        )
    ];
    "context", StructureCase( "databaseName", "eqsnap" );
);

// Serialize for sending
Request Body = jsonify( Payload, JSON_DATE_FORMAT_ISO_8601, JSON_TIME_FORMAT_ISO_8601 );
Print( Request Body, "\n" );

// After receiving a response string, parse it
Response = unjsonify( Response String );
```

You can also compose the JSON inline with `$$...$` and parse directly:

```slang
Request = unjsonify( $$
{
    "functions": [ "GetPrice" ],
    "arguments": [
        {
            "ticker": "AAPL",
            "date": "2026-01-15"
        }
    ]
}
$ );
```

---

## String Escaping for JSON

If you need to embed a Slang string inside a manually-constructed JSON string
(not recommended -- prefer `jsonify`), use `@String::JSON Escape` from
`_LIB String Functions`:

```slang
Link( "_LIB String Functions" );

Raw = "He said \"hello\"\nand left";
Escaped = @String::JSON Escape( Raw );
// Escaped = "He said \\\"hello\\\"\\nand left"

// Manual JSON construction (prefer jsonify instead)
Json = "{\"message\":\"" + Escaped + "\"}";
```

---

## Quick Reference

| Task | Code |
|------|------|
| Serialize to JSON | `jsonify( value )` |
| Serialize with dates | `jsonify( value, JSON_DATE_FORMAT_ISO_8601, JSON_TIME_FORMAT_ISO_8601 )` |
| Parse JSON string | `unjsonify( str )` |
| Parse with booleans | `unjsonify( str, unwrapBooleanAsBoolean := true )` |
| Inline JSON literal | `unjsonify( $$ { "key": "val" } $ )` |
| Link format constants | `Link( "_TYPE JSON String" );` |
| Escape string for JSON | `@String::JSON Escape( str )` (requires `_LIB String Functions`) |
