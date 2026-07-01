# Slang Syntax Guide

Use the following information about Slang syntax, data types, operators, control flow, functions, and coding style to guide your code generation.

---

## Language Overview

- **Single-threaded:** Slang is a single-threaded language.
- **Dynamically Typed:** Functions handle type checking. Variables are implicitly created upon assignment. The type of the implicitly created variable is *not* declared explicitly but rather determined by the type of the expression on the right hand side of the assignment. Strong typing is optional for function parameters and return types.
- **Extensible Core Functions:** Also known as built-in functions. The set of built-in functions is growing, and user-defined functions can be added.
- **Scoping:** Variables can be global, local, private, or named.
- **Reflection:** Programs can examine data values and objects.
- **Diddling:** Temporary value alteration and restoration (SecDb feature).
- **Run-time Script Creation:** New scripts can be created from within other scripts.
- **Functions are Variables:** Functions are assigned to variables and can return other functions.
- **Everything Returns Something:** No `void` type.
- **Operator Overloading:** Operators behave differently based on data types.

---

## Syntax Basics

- Statements are terminated with a semicolon ( `;` ).
- A block is enclosed in curly braces ( `{}` ) and returns a value.
- Blocks are also terminated with a semicolon.
- Must use spaces with round brackets `()` ( e.g., `If( X )`, `@Private::My Func( X )`, `Print( Y )`, `Return( Z )`, `X = ( A * B ) + ( C * D )`, and wherever possible ).
- Must use spaces with square brackets `[]` ( e.g., `My Array[ I ]` ).
- `else` is represented by the `:` operator.
- Catch blocks of Try-Catch are also represented by `:`.
- Spaces are allowed in symbol names.
- Slang symbol names (e.g. function names, and variable names) *must* contain only alphanumeric characters, underscores, and spaces (and `$`, provided it is not the first character). E.g. `pre-order` is *not* allowed, `$foo` is *not* allowed. `foo$` is allowed.
- Slang is unique in that it allows "spaces" in function and variable names. Always prefer using space separated variable names and function names. E.g., `My Variable = 5`, `Get Value = Func()`. Note: "camel case" and other naming methods are not preferred.
- Variable names are case-insensitive (but consistency must be followed).

### CRITICAL WARNING: Avoiding Variable Type Hallucinations

Slang is a **dynamically typed** language. Variables are **NEVER** declared with a type prefix like in Java or C++. The type is always inferred from the value being assigned.

A common point of confusion is variable naming. A variable named `String My Data` is a **single variable** whose full name is "String My Data". It is **NOT** a variable named `My Data` of type `String`.

**TO PREVENT ERRORS, YOU MUST AVOID STARTING VARIABLE NAMES WITH A SLANG DATA TYPE.**

- **INCORRECT AND AMBIGUOUS:** `String Customer Name = "John Doe";`
- **CORRECT AND UNAMBIGUOUS:** `Customer Name String = "John Doe";` or `Customer Name = "John Doe";`

**Examples:**

```slang
// Example 1
Names List String = "Albert, Bob, Carol, Daniel, Elaine, Frank";
Extracted Names Array = @Private::Extract Names( Names List String );

// Example 2
Text To Search = "The cat sat on the mat. The fat cat ate a rat.";

// Example 3
Search Array = [ "cat", "dog", "rat" ];
Found Index = @Array::FindByValue( &Search Array, "dog" );

// Example 4
First Structure = {| "Name" := "Alice", "Age" := 30 |};
Second Structure = {| "City" := "New York", "Occupation" := "Engineer" |};
Merged Structure = First Structure ++ Second Structure;
```

### Function Calls

- Functions are defined using `Func`.
- Non built-in functions defined in `user-defined` and `standard slang` library are called with `@`. ( e.g., `@Array::Split( Array, 5 )` ).
- Built-in Functions are called without `@`. ( e.g., `ArrayConcat( Array 1, Array 2 )` ).
- Member functions of a `Typed Structure` library are called using `.` operator. ( e.g., `Instance = Namespace::Type Name(); Instance.Function();` ).
- In-line comments start with `//`, and there must be a space after `//`. ( e.g., `// This is a test function` ).

### Example Syntax

```slang
/****************************************************************
**  Routine: Private::Get Famous Saying
**
**  Program to retrieve a famous saying based on an integer
****************************************************************/
Private::Get Famous Saying = Func(
    Double( Seed ),
)
Returns( String() )
{
    If( Mod( Seed, 2 ) == 0 )
    {
        Famous Saying = "The only thing we have to fear is fear itself";
    }
    : // colon (`:`) replaces `else` here
    {
        Famous Saying = "Only you can prevent forest fires";
    }; // blocks are terminated with semicolon (`;`)

    If( Mod( Seed, 3 ) == 0 )
    {
        Famous Saying = "You have selected you referring to me. That is incorrect. The correct answer is you.";
    }; // blocks are terminated with semicolon (`;`)

    Return( Famous Saying );
};
Saying = @Private::Get Famous Saying( 4 );
Print( Saying );
```

---

## Operators

| Category | Operators |
| :--- | :--- |
| **Arithmetic** | `+`, `-`, `*`, `/`. Use `Mod` for modulo, `Pow` for power. |
| **Unary** | `-` (negative), `!` (not), `++` (increment), `--` (decrement). |
| **Assignment** | `=`, `+=`, `-=`, `*=`, `/=`, `&=` (append). |
| **Comparison** | `==`, `<`, `>`, `<=`, `>=`, `!=`, `<=>` (compare: -1, 0, 1). |
| **Logical** | `&&` (AND), `||` (OR), `!` (NOT is also a boolean operator). |

### Special Operators

- `@` -- Calls a non built-in (user-defined) function.
- `&` -- Passes arguments by reference.
- `::` -- References a scoped variable ( e.g., `Trade Execution::Date` ).
- `[]` -- Accesses an array component by index ( e.g., `Fruits[ 2 ]` ); Accesses a structure value by variable name ( e.g., `S = {| "foo" := "bar" |}; X = "foo"; S[ X ]` ).
- `.` -- Accesses a datatype value by key (or component) from a structure (e.g., `Banana.Calories`). It is also used to access data members and call member functions of `Typed Structures`. Use the dot operator (`.`) for direct member access in structures when the key is known and is a valid symbol name (e.g., `My Struct.Key 1`). This is the preferred and more performant method when the key is a literal. Do *NOT* combine the dot operator and square brackets like this: `My Struct.[ "Key 1" ]`. This syntax is incorrect. Use square brackets (`[]`) for dynamic access in structures when the key is a variable (i.e., `X = "Key 1"; My Struct[ X ]`).

---

## Data Types

| Type | Description |
| :--- | :--- |
| `Array` | Array of values. |
| `Binary` | Binary memory block. |
| `Curve` | Indexed collection of dates and values. |
| `Date` | Date (DDMMMYYYY format). E.g., `Date( "17Apr2025" )`. |
| `Double` | Number (all numeric values in Slang are represented in Double format). Can represent boolean values using `True` (1) and `False` (0). Does not accept `TrueBool` or `FalseBool`. |
| `Null` | Null value. |
| `RDate` | Relative Date (e.g., `3b` for three business days). |
| `Slang` | Parsed Slang expression. |
| `String` | Character String. |
| `Structure` | Structure of values. |
| `Time` | Time (DayOfWeek Date HH:MM:SS am/pm). |
| `Boolean` | Boolean Values. Only accepted values are `TrueBool`, `FalseBool`. Will *not* accept `True` or `False`. |

### Example Data Type Usage

```slang
X = 3; // Create a double with value 3
Y = String( x );  // Cast x to a string
// Example demonstrating how to find the length of a string using the Size() function
Test String = "This is a test string";  // Define a string variable
Length Of String = Size( Test String );  // Find the length of the string
First Part = "Hello, ";
Second Part = "world!";
Concatenated String = First Part + Second Part;  // Concatenate two strings
Print( "The length of the string is: ", Length Of String, "\n" );  // Print the length of the string
Print( "The type of the length is: ", TypeOf( Length Of String ), "\n" );  // Print the type of the length
Print( "The concatenated string is: ", Concatenated String, "\n" );  // Print the concatenated string
// The output will be:
// The length of the string is: 21
// The type of the length is: Double
// The concatenated string is: Hello, world!
Y = "3"; // Creates a string with value "3"
Z = Null; // Creates a null value
// To construct a `Date` object in Slang, you use the built-in `Date()` constructor function.
// The idiomatic format for the date string passed into the `Date()` function is `DDMMMYYYY`.
//   DD:   Day of the month (e.g., 01, 15, 31).
//   MMM:  Abbreviated month name (e.g., Jan, Feb, Mar). Case-insensitive.
//   YYYY: Year (e.g., 2023, 2024, 2025).
// Valid examples: Date( "29Apr2025" ), Date( "01JAN2024" ), Date( "17aug2023" ).
My Date = Date( "10Apr2025" );
Print( "Month: ", My Date.Month, "\n" ); // Output: Month: 4
Print( "Day: ", My Date.Day, "\n" ); // Output: Day: 10
Print( "Year: ", My Date.Year, "\n" ); // Output: Year: 2025
My Array = [ "value1", 2, My Date ]; // Creates an Array with 3 values. Arrays are not strongly typed.
My Struct = {| Name := "Example", Value := 123 |}; // Creates a structure with Keys Name and Value.

// To determine the data type of a variable in Slang, use the TypeOf() function.
Print( "Type of X: ", TypeOf( X ), "\n" ); // Output: Type of X: Double
Print( "Type of Y: ", TypeOf( Y ), "\n" ); // Output: Type of Y: String
Print( "Type of Z: ", TypeOf( Z ), "\n" ); // Output: Type of Z: Null
Print( "Type of My Date: ", TypeOf( My Date ), "\n" ); // Output: Type of My Date: Date
Print( "Type of My Array: ", TypeOf( My Array ), "\n" ); // Output: Type of My Array: Array
Print( "Type of My Struct: ", TypeOf( My Struct ), "\n" ); // Output: Type of My Struct: Structure
```

---

## Functions, Control Flow, and Program Structure

- **Core vs. User-Defined Functions:** Core functions are built-in; user-defined functions are script-specific.
- **Core/Built-in Functions** are also referred to as `Addins`.
- **`Func`:** Used to define functions.
- **`Return`:** Every function must return a value using `Return`.
- **`Returns`:** Used to specify return type of a function.
- **Arguments:** Arguments can have specific data types, have default values, and be named.
- **Constants:** Use `Constant( ConstantName, Value )` to define constants. Use `EvalOnce` to mark expressions as constant.
- **`Link`:** Includes another script (similar to `#include`). Use `SmartLinkEnable()` in library scripts.
- **Scope:** Global, Local, Private, Named. Use `::` to access scoped variables. Prefer to use `Private` scope for top-level functions and variables unless they should be accessible from other scripts.
- **`Lambda`:** Anonymous functions can be defined using the `Lambda()` keyword.
- Opening and closing curly braces `{` , `}` must always go on a new line.

### Control Flow Examples

**If / Else:**

```slang
If( condition )
{
    block1
}
:
{
    block2
};
```

**Inline If (Ternary Equivalent):**

Slang does **not** have a C-style ternary operator (`? :`). Instead, use an inline `If` expression. Because everything in Slang returns a value, `If` can be used directly inside expressions:

```slang
// Inline If as an expression -- returns "Yes" or "No"
Label = If( Score > 50 ) "Pass" : "Fail";

// Inside a function call
Print( If( Is Active ) "ON" : "OFF", "\n" );

// Nested inline If
Grade = If( Score >= 90 ) "A" : If( Score >= 80 ) "B" : "C";
```

> **CRITICAL:** Never use the C-style ternary syntax `condition ? value1 : value2`. It is **not valid Slang**. Always use `If( condition ) value1 : value2`.

**While:**

```slang
While( condition )
{
    block
};
```

**For:**

```slang
For( initializer; condition; modifier )
{
    block
};
```

**ForEach:**

```slang
My Array = [ 1, 2, 3, 4, 5 ];
ForEach( Element, My Array )
{
    Print( Element );
};
```

**ForComponent (iterate structure keys):**

```slang
My Struct = {| "Name" := "John", "Age" := 30 |};
ForComponent( Key, My Struct )
{
    Print( Key, " = ", My Struct[ Key ], "\n" );
};
// This loop prints each key-value pair in the structure.
```

**ForComponentValue (iterate structure key-value pairs):**

```slang
My Struct = {| "Name" := "John", "Age" := 30 |};
ForComponentValue( Key, Value, My Struct )
{
    Print( Key, " = ", Value, "\n" );
};
// This loop prints each key-value pair in the structure.
```

**Switch:**

```slang
Switch( Language,
    "EnglishFull",                  Return( DateFns::MonthsFull );
    Each( [ "English", "Short" ] ), Return( DateFns::Months );
                                    Throw( Err( Sprint( "Unknown option type" ) ) ); // Default case
);
```

Switch uses a comma separated list of cases, each of which can be a single value or a function. The `Each` keyword allows an array of values to be matched.

**Typecase:**

Typecase is a control flow mechanism that allows branching logic based on the runtime data type of an expression. It operates similarly to a Switch statement but evaluates types rather than specific values. This is particularly useful in dynamically typed languages like Slang for handling polymorphic data and implementing type-specific behavior. Typecase is a built-in function, meaning it is called directly without the `@` prefix.

```slang
Typecase( Expression )
: Case( DataType( Variable Name ) )
{
    // Code to execute if Expression matches DataType
    // 'Variable Name' holds the value of Expression, cast to 'DataType'
}
: Case( Another DataType( Another Variable Name ) )
{
    // ... additional type-specific cases ...
}
: // Optional default case for any unmatched type
{
    // Code to execute if no other type matches
};
```

> **Important Note on Each:** The `Each` keyword is specifically designed for use within Switch statements to match an array of values against a case. Each does **not** work with Typecase. Typecase evaluates the data type of an expression, not its value, and its Case clauses expect a single data type for matching.

**Try / Catch:**

```slang
Try( Exception Variable )
{
    // Code that may raise an exception
}
:
{
    // Code to handle the exception
    // Access exception information through 'Exception Variable'
    // e.g., Print( "Error: ", Exception Variable.Describe( True ) );
};
```

### Function Definition Examples

```slang
/****************************************************************
**  Routine: Private::Print Sum
**
**  Prints the sum of two numbers.
**  PrintSum does not return a value.
****************************************************************/
Private::Print Sum = Func(
    Double( Number 1 ),
    Double( Number 2 ),
)
Returns()
{
    Print( Number 1 + Number 2, "\n" );
};

/****************************************************************
**  Routine: Private::Add Two Numbers
**
**  Adds two numbers and returns the result.
****************************************************************/
Private::Add Two Numbers = Func(
    Double( Number 1 ),
    Double( Number 2 ),
)
Returns( Double() )
{
    Return( Number 1 + Number 2 );
};

/****************************************************************
**  Routine: Private::Recursive Function
**
**  Calculates the factorial of a number using recursion.
**  Note: Recursion is not directly possible with a local scope
**  in Slang. Local variables are function-specific, and each
**  recursive call creates new instances, preventing access to
**  previous states. To enable recursion, define the function in
**  a broader scope like Global, Private, or a Named scope,
**  allowing persistent variable access across calls.
****************************************************************/
Private::Recursive Function = Func(
    Double( Counter )
)
Returns( Double() )
{
    If( Counter <= 0 )
    {
        Return( 1 );
    }
    :
    {
        Return( Counter * @Private::Recursive Function( Counter - 1 ) );
    };
};

Print( @Private::Recursive Function( 5 ) ); // Output: 120

X = 5;
If( X > 0 )
{
    Print( "X is positive" );
}
:
{
    Print( "X is not positive" );
};

For( I = 0; I < 10; I++ )
{
    Print( I );
};

Try( Ex )
{
    X = 5;
    If( X < 5 )
        Throw( Err( Sprint( "X is less than 5" ) ) );
}
:
{
    Printf( "Exeception Occured : %s", Ex.lastError );
}
```

---

## Lambda Functions

**Using the `Lambda()` keyword:**

```slang
My Lambda = Lambda() Returns( String() ) { Return( "hello" ); };
```

**Using the `\` and `->` shorthand syntax:**

```slang
My Lambda = \x -> x * x;
Result = @My Lambda( 5 ); // Result is now 25
```

**Multiple arguments:**

```slang
My Lambda = \x, y -> ( x * y ); // Multiplies 2 numbers x and y
Result = @My Lambda( 5, 8 ); // Result is now 40
```

---

## Function Arguments: Positional vs. Named

Slang functions support three types of arguments, which must be declared in a specific order: required positional, optional positional, and named. This structure provides a blend of simplicity for basic functions and flexibility for complex ones.

### Argument Types and Definition Order

When defining a function, arguments must be listed in the following strict order:

1. **Required Positional Arguments:** Standard arguments that must be provided by the caller in the correct position. They have no default value.
   - Syntax: `DataType( Argument Name )`

2. **Optional Positional Arguments:** Positional arguments that have a default value specified with the `=` operator. Callers can omit them, and the default value will be used.
   - Syntax: `DataType( Argument Name ) = Default Value`

3. **Named Arguments:** Arguments identified by name rather than position when the function is called. They must have a default value specified with the `:=` operator.
   - Syntax: `DataType( Argument Name ) := Default Value`

A function can have any combination of these, as long as the order is maintained. A function cannot have a required positional argument after an optional or named one.

### Key Differences

| Feature | Optional Positional (`=`) | Named (`:=`) |
| :--- | :--- | :--- |
| **Definition** | `Arg = "default"` | `Arg := "default"` |
| **Calling** | By position | By name (`Arg := value`) |
| **Order** | Flexible for caller | Any order after positionals |
| **Null Override** | Does **not** override default | **Does** override default |

### Calling Functions with Mixed Arguments

When calling a function, you must provide all required positional arguments first, in order. You can then provide optional positional arguments by position, or skip them to use their defaults. Finally, you can provide named arguments in any order.

### Special Case: Ellipsis for Variadic Functions

Slang supports a variable number of arguments using `Ellipsis()`. An ellipsis argument collects all extra arguments. It must be the **last positional argument** in a function definition and cannot be followed by other positional or named arguments.

```slang
// Example of an Ellipsis argument
My Sum = Func( Ellipsis( Numbers ) = [] )
{
    Return( Sum( Numbers ) );
};
```

### Full Example

The following code defines a hybrid function and demonstrates how to call it.

```slang
/****************************************************************
**  Routine: Private::Calculate Cost
**
**  Demonstrates a function with required positional, optional
**  positional, and named arguments.
****************************************************************/
Private::Calculate Cost = Func(
    // 1. Required positional argument
    String( Item Name ),

    // 2. Optional positional argument
    Double( Quantity ) = 1.0,

    // 3. Named arguments
    Double( Unit Price ) := 10.0,
    Boolean( Apply Tax ) := TrueBool
)
Returns( Double() )
{
    // Calculate base cost
    Total Cost = Quantity * Unit Price;

    // Apply tax if the flag is set
    If( Apply Tax )
    {
        Total Cost *= 1.08; // Apply 8% tax
    };

    Print( "Cost for ", Quantity, " '", Item Name, "' is: ", Total Cost, "\n" );
    Return( Total Cost );
};

// --- Calling the function in various ways ---

// 1. Using only the required argument. Others use defaults.
// Prints: Cost for 1 'Apple' is: 10.8
@Private::Calculate Cost( "Apple" );

// 2. Providing both positional arguments.
// Prints: Cost for 3 'Apple' is: 32.4
@Private::Calculate Cost( "Apple", 3.0 );

// 3. Overriding a named argument. Note the := syntax.
// Prints: Cost for 1 'Banana' is: 15
@Private::Calculate Cost( "Banana", Unit Price := 15.0, Apply Tax := FalseBool );

// 4. Providing an optional positional and a named argument.
// Prints: Cost for 5 'Orange' is: 81
@Private::Calculate Cost( "Orange", 5.0, Unit Price := 15.0 );

// 5. Named arguments can be in any order.
// Prints: Cost for 1 'Grape' is: 20
@Private::Calculate Cost( "Grape", Apply Tax := FalseBool, Unit Price := 20.0 );

// 6. INVALID: A positional argument cannot follow a named argument.
// This call will fail.
Try( E )
{
    @Private::Calculate Cost( "Failing Item", Unit Price := 5.0, 2.0 );
}
:
{
    Print( "Caught expected error: ", E.Describe(), "\n" );
};
```

---

## Finally Blocks

The `Finally` block provides a mechanism to execute cleanup code after a function exits, regardless of whether it exits normally via a `Return` statement or due to an unhandled `Throw` statement. It is attached to a function definition and is primarily used for resource management, such as closing file handles or database connections.

The `Finally` block is syntactically placed after the main function body, preceded by a colon (`:`).

### Syntax

```slang
My Function = Func( ... )
Returns( ... )
{
    // Main function body.
    // This block may contain a Return statement or Throw an exception.
}
: Finally()
{
    // Cleanup code.
    // This block is executed after the main body,
    // both on normal return and on an unhandled exception.
};
```

### Execution Guarantees and Example

The code within a `Finally` block is guaranteed to run when the function it is attached to terminates through either a `Return` or an unhandled `Throw`.

The following example demonstrates a function that creates and writes to a temporary file. The `Finally` block ensures the file handle is destroyed and the file is deleted, even if an error is thrown during processing.

```slang
/****************************************************************
**  Routine: Private::Process File
**
**  Demonstrates the use of a Finally block for cleanup.
**  It creates a temporary file and ensures it is cleaned up,
**  regardless of whether an error is thrown.
****************************************************************/
Private::Process File = Func(
    Boolean( Should Throw Error )
)
Returns()
{
    // Create a temporary file name. The file will be created in the system's temp directory.
    Temp File Name = FileTempName();

    // Open the temporary file for writing.
    File Handle = FileOpen( Temp File Name, FILE_OPEN_WRITE );
    Print( "File '", Temp File Name, "' opened successfully.\n" );

    // Write some content to the file.
    FileWrite( File Handle, "This is a test." );

    // If the flag is set, throw an error to simulate a failure condition.
    If( Should Throw Error )
    {
        Throw( Err( "Simulating an error during file processing." ) );
    };

    Print( "File processing completed without errors.\n" );
}
: Finally()
{
    // The Finally block is executed after the function body,
    // ensuring cleanup happens in all cases (normal return or exception).

    // Check if the file handle is valid before trying to destroy it.
    If( !IsError( File Handle ) )
    {
        Destroy( File Handle );
    };

    // Check if the file exists before trying to delete it.
    If( FileExists( Temp File Name ) )
    {
        FileDelete( Temp File Name );
    };

    Print( "Finally block executed: Cleanup for '", Temp File Name, "' is complete.\n" );
};

// --- Demonstration ---

// Case 1: Successful execution (no error thrown)
Print( "--- Running successful case ---\n" );
Try( E1 )
{
    @Private::Process File( FalseBool );
}
:
{
    Print( "Caught unexpected exception: ", E1.Describe(), "\n" );
};

// Case 2: Execution with a thrown error
Print( "\n--- Running failure case ---\n" );
Try( E2 )
{
    @Private::Process File( TrueBool );
}
:
{
    // The exception thrown inside Process File is caught here.
    Print( "Caught expected exception: ", E2.Describe(), "\n" );
};
```

---

## Checking for Errors with IsError

The built-in function `IsError` is the canonical and most reliable way to determine if a variable holds an error value or null. It should be used to check the results of operations that might fail, such as function calls or calculations.

### Why Use `IsError`?

While some error conditions might be represented by the constant `Error Value`, this is not exhaustive. For example, a `Double` can also be in an error state if it is `NaN` (Not a Number) or negative infinity. A direct comparison like `My Variable == Error Value` will fail to detect these other error states. `IsError` correctly identifies all of them.

Furthermore, `IsError` also returns `True` for the `Null` value, providing a single, robust function to check for both error and null conditions.

However, `IsError()` is only meaningful for a specific set of data types that can represent an error state. For any other type, `IsError()` will always return `False`, and the linter will flag this check as a pointless error.

### Types Supporting `IsError`

`IsError()` is meaningful only for the following types:

- `Any()`
- `Date()`
- `Double()`
- `Each()`
- `Error()`
- `Error Result()`
- `FixedPointQuantity()`
- `GsDt()`
- `GsTick()`
- `Index Pos()`
- `NoArg()`
- `Null`
- `OClock()`
- `RDate()`
- `Reference()`
- `SDB::Position Quantity()`
- `SDB::Remote Stream Reference()`
- `SDB::Timestamp()`
- `SDB::Unique ID64()`
- `SecDb Node()`
- `Security()`
- `Slang()`
- `Slang Node()`
- `Socket()`
- `STRegTestType()`
- `Time()`
- `TsInputPoint()`
- `UDPSocket()`
- `Value Type Info()`

> **Note:** The slang type `Database()` does not implement `IsError()`, and checking it is a lint error.

### CRITICAL: `IsError` vs. Direct Comparison

- **INCORRECT (Anti-Pattern):** `If( Result == Error Value ) { ... }`
- **CORRECT (Robust):** `If( IsError( Result ) ) { ... }`

### Common Use Cases

#### 1. Checking Function Return Values

Many functions, especially those interacting with databases or files (e.g., `GetSecurity`, `FileOpen`), return an error value on failure. You should always check their return values with `IsError`.

```slang
// This example demonstrates checking the return value of GetSecurity.
Security Name = "NonExistentSecurity";
Sec = GetSecurity( Security Name );

// Check if the GetSecurity call failed. IsError returns True for Null or Error types.
If( IsError( Sec ) )
{
    // Handle the error, e.g., print the last error message and stop.
    Print( "Failed to retrieve '", Security Name, "'. Error: ", LastError(), "\n" );
}
:
{
    // Proceed with the valid security object.
    Print( "Successfully retrieved '", Security Name, "'.\n" );
};
```

#### 2. Validating Function Arguments

Before performing operations inside a function, it is good practice to validate the incoming arguments to ensure they are not in an error state.

```slang
/****************************************************************
**  Routine: Private::Calculate Ratio
**
**  Calculates the ratio of two numbers, with error checking.
****************************************************************/
Private::Calculate Ratio = Func(
    Double( Numerator ),
    Double( Denominator )
)
Returns( Double() )
{
    // Validate the denominator argument.
    If( IsError( Denominator ) || Denominator == 0 )
    {
        // Return an error value if the denominator is invalid.
        Return( ErrD( "Invalid denominator provided." ) );
    };

    // Also validate the numerator.
    If( IsError( Numerator ) )
    {
        Return( ErrD( "Invalid numerator provided." ) );
    };

    Return( Numerator / Denominator );
};

// --- Demonstration ---
Result1 = @Private::Calculate Ratio( 10, 2 );
Print( "10 / 2 = ", Result1, "\n" ); // Output: 10 / 2 = 5

Result2 = @Private::Calculate Ratio( 10, 0 );
If( IsError( Result2 ) )
{
    Print( "Caught expected error for division by zero: ", LastError(), "\n" );
};
```

---

## Arrays, Structures, and StructureCase

- Arrays are created using `Array()` or `[]`. Always prefer `[]` to `Array()` for creating an Array.
- Structures are created using `Structure()` or `{| ... |}`. Always prefer `{| ... |}` to `Structure()` for creating a Structure.
- StructureCase are created using `StructureCase()` or `{\ ... \}`. Always prefer `{\ ... \}` to `StructureCase()` for creating case sensitive Structures.

> **Note:** Backslashes used for creating StructureCase are part of syntax and not escape characters. Do not escape the backslashes.
>
> - **Incorrect Syntax:** `My Case Sensitive Struct = {\\ "Key" := "value" \\};`
> - **Correct Syntax:** `My Case Sensitive Struct = {\ "Key" := "value" \};`

- Structure and StructureCase must have string keys; StructureCase keys are case-sensitive.
- Access elements using `[]` or `.` (Structures and StructureCase). The `.` accessor is faster. Always prefer `.` over `[]`.
- Access elements using `[]` (Arrays).
- Arrays can be concatenated using the `++` operator:

```slang
My Array1 = [ 1, 2, 3 ];
My Array2 = [ 4, 5, 6 ];
My Array3 = My Array1 ++ My Array2;
// My Array3 will be [ 1, 2, 3, 4, 5, 6 ]
```

- Special `Structure` and `StructureCase` member functions: `Keys()`, `Values()`, `UnsortedKeys()`.
- The union of two Structures or StructureCases can be computed using the infix `++` operator; for keys that are present in both structures, the result has the value of the l.h.s. argument:

```slang
S1 = {| a := 1, b := 2 |};
S2 = S1 ++ {| b := 3, c := 4 |};
// S2 will be {| a := 1, b := 2, c := 4 |}
```

- To remove a component from a Structure or StructureCase, use the `Destroy` function:

```slang
S = {| a := 1, b := 2, c := 3 |};
Destroy( S.b ); // Removes the component 'b' from the structure
// S will now be {| a := 1, c := 3 |}
```

- Built-in Functions: `ArrayInsert`, `ArrayDelete`, `ArrayExtract`, `Sort`, `ArrayUnique`, `StructureUnion`, `TableInit`, `SortTable`.

### Example: Arrays and Structures

```slang
My Array = [ "apple", "banana", "cherry" ];
Print( My Array[ 0 ] ); // Output: apple

My Struct = {|
    "Name" := "John",
    "Age" := 30
|};
Print( My Struct[ "Name" ] ); // Output: John
Print( My Struct.Name ); // Output: John

Case Sensitive Struct = {\ "Name" := "John", "Age" := 30 \};
Print( Case Sensitive Struct[ "Name" ] ); // Output: John
Print( Case Sensitive Struct.Name ); // Output: John
```

### Example: Array and Structure Built-in Functions

```slang
// ArrayInsert: Inserts elements into an array
My Array = [ "apple", "banana", "cherry" ];
Print( "Original Array: ", My Array, "\n" ); // Output: Original Array: [0] = apple [1] = banana [2] = cherry
Index = 1; // The index of the existing element to insert before.
Count = 2; // Number of elements to insert. Defaults to 1, if omitted.
ArrayInsert( My Array, Index, Count ); // Insert two null elements before index 1
Print( "Array after insertion: ", My Array, "\n" ); // Output: Array after insertion: [0] = apple [1] = null [2] = null [3] = banana [4] = cherry
My Array[ 1 ] = "grape"; // Assign value to the first inserted element
My Array[ 2 ] = "orange"; // Assign value to the second inserted element
Print( "Array after assigning values: ", My Array, "\n" ); // Output: Array after assigning values: [0] = apple [1] = grape [2] = orange [3] = banana [4] = cherry

// ArrayExtract: Extracts a portion of an array
My Array = [ 1, 2, 3, 4, 5, 6 ];
Index = 2; // Starting index
Count = 3; // Number of elements to extract
Extracted Array = ArrayExtract( My Array, Index, Count );
Print( Extracted Array ); // Output: [ 3, 4, 5 ]

// ArrayDelete: Deletes elements from an array
ArrayDelete( My Array, 2, 1 ); // Delete one element starting from index 2
Print( "Array after deletion: ", My Array, "\n" ); // Output: Array after deletion: [0] = 1 [1] = 2 [2] = 4 [3] = 5 [4] = 6

// Sort: Sorts the contents of an array
My Array 2 = [ 3, 1, 4, 1, 5, 9, 2, 6 ];
Print( "Original Array: ", My Array 2, "\n" ); // Output: Original Array: [0] = 3 [1] = 1 [2] = 4 [3] = 1 [4] = 5 [5] = 9 [6] = 2 [7] = 6
Sort( My Array 2 ); // Sort the array in ascending order
Print( "Sorted Array: ", My Array 2, "\n" ); // Output: Sorted Array: [0] = 1 [1] = 1 [2] = 2 [3] = 3 [4] = 4 [5] = 5 [6] = 6 [7] = 9

// ArrayUnique: Eliminates duplicate elements within an array
My Array 3 = [ 1, 2, 2, 3, 4, 4, 5 ];
Print( "Original Array: ", My Array 3, "\n" ); // Output: Original Array: [0] = 1 [1] = 2 [2] = 2 [3] = 3 [4] = 4 [5] = 4 [6] = 5
ArrayUnique( My Array 3, True ); // Sorts the array first and then removes duplicates
Print( "Array with unique elements: ", My Array 3, "\n" ); // Output: Array with unique elements: [0] = 1 [1] = 2 [2] = 3 [3] = 4 [4] = 5

// StructureUnion: Creates a union between two structures
Struct 1 = {| "Name" := "John", "Age" := 30 |};
Struct 2 = {| "Age" := 40, "City" := "New York", "Occupation" := "Engineer" |};
Print( "Struct 1: ", Struct 1, "\n" );
// Output:
// Struct 1: Age : 30
// name: John
Print( "Struct 2: ", Struct 2, "\n" );
// Output:
// Struct 2: Age       : 40
// City      : New York
// Occupation: Engineer

StructureUnion( Struct 1, Struct 2 ); // Perform the union operation
Print( "Union of Struct 1 and Struct 2: ", Struct 1, "\n" );
// Output:
// Union of Struct 1 and Struct 2: Age       : 30
// City      : New York
// name      : John
// Occupation: Engineer

// TableInit: Initializes a special type of array called a TableInit array
Employee Info = TableInit( [
    [ "Name", "Date Of Hire" ],
    [ "Peter Smith", Date( "01Jan1999" ) ],
    [ "John Brown", Date( "25Apr1997" ) ],
    [ "David Jones", Date( "19Oct2000" ), "Place", "New York" ],
] );
Print( "TableInit Array: ", Employee Info, "\n" );
// Output:
// TableInit Array: [   0] = Date Of Hire:  1Jan99
//          name        : Peter Smith
//
// [   1] = Date Of Hire: 25Apr97
//          name        : John Brown
//
// [   2] = Date Of Hire: 19Oct00
//          name        : David Jones
//          Place       : New York

// SortTable: Sorts an array of structures by structure component
Data = [
    {| "Name" := "Charlie", "Age" := 25 |},
    {| "Name" := "Alice", "Age" := 35 |},
    {| "Name" := "Bob", "Age" := 30 |}
];
Print( "Original Data: ", Data, "\n" );
// Output:
// Original Data: [   0] = Age : 25
//          name: Charlie
//
// [   1] = Age : 35
//          name: Alice
//
// [   2] = Age : 30
//          name: Bob
SortTable( Data, [ "Age" ] ); // Sort the array of structures by the "Age" component
Print( "Data sorted by Age: ", Data, "\n" );
// Output:
// Data sorted by Age: [   0] = Age : 25
//          name: Charlie
//
// [   1] = Age : 30
//          name: Bob
//
// [   2] = Age : 35
//          name: Alice
```

---

## Dollar-Sign String Literals

In addition to standard double-quoted strings (e.g., `"Hello, World!"`), Slang offers a powerful alternative syntax for defining string literals, often called "dollar-sign strings." This syntax allows you to specify a custom delimiter for the string, which is useful for creating strings that contain characters that would otherwise need to be escaped, such as `"` or `\`.

> **Note:** Double-quoted strings are the preferred way to define strings in Slang, but dollar-sign strings provide a convenient alternative when dealing with complex string content.

### Syntax

A dollar-sign string is defined by a `$` character, immediately followed by your chosen delimiter character, the string content, and the same delimiter character to terminate the string.

```
$<delimiter><string_content><delimiter>
```

- **`<delimiter>`**: Can be almost any single character. Common choices include `|`, `!`, `#`, `~`, or even another `$`. The character immediately following the initial `$` sets the delimiter for that specific string.
- **`<string_content>`**: The literal content of the string. No characters within the string are treated as special or need escaping, with the one exception of the delimiter character itself.

> **CRITICAL NOTE ON DELIMITERS:** The closing delimiter is **always a single character** that matches the character immediately following the initial `$`. Even when a convention like `$$` is used to open a string, the closing delimiter is only a single `$`. The symmetric form `$$string$$` is **invalid Slang syntax**.
>
> - **Correct:** `MyString = $$This is correct.$;`
> - **Invalid:** `MyString = $$This is incorrect$$;`

### Usage and Examples

This feature simplifies the creation of strings containing quotes, file paths, or regular expressions.

1. **String with Double Quotes:**
   - **Standard:** `My String = "He said, \"Hello!\"";`
   - **Dollar-Sign:** `My String = $|He said, "Hello!"|;` (using `|` as the delimiter)

2. **Multiline Strings:**
   A common convention for multiline strings is to use the `$` character itself as the delimiter. This results in an opening sequence of `$$` and a closing delimiter of a single `$`.
   ```slang
   My Multiline String = $$This is the first line.
   This is the second line.
   And this is the third.$;
   ```

3. **String with Various Special Characters:**
   To create a string containing `$` and `"`, pick a delimiter that is not present in your string content.
   ```slang
   My Special String = $#This string contains a "quote" and a $ dollar sign.#;
   ```

The key rule is that the only character you cannot use inside the string is the delimiter you've chosen for it.

### Code Example

```slang
// This script demonstrates the use of alternative delimiters for string literals in Slang.

// Example 1: Using '|' as a delimiter to include double quotes without escaping.
Example = $|This is a string that contains "double quotes" without any issue.|;
Print( "String with '|' delimiter: ", Example, "\n" );

// Example 2: Using '!' as a delimiter. This is useful for strings containing other common symbols.
File Path = $!C:\Users\Test\My "Special" Folder\notes.txt!;
Print( "String with '!' delimiter: ", File Path, "\n" );

// Example 3: Using '#' as a delimiter to include both single and double quotes, and a dollar sign.
Complex String = $#'A string with "double quotes", 'single quotes', and a $ sign.'#;
Print( "String with '#' delimiter: ", Complex String, "\n" );

// Example 4: Using '$' as the delimiter for a string that contains special characters.
Special Characters String = $$This string contains a "quote" without escaping.$;
Print( "String with '$' delimiter:\n", Special Characters String, "\n" );

// Example 5: Using '$' as the delimiter for a multiline string.
// This is a common and readable convention.
Multiline String = $$This is the first line.
This is the second line.
This string literal spans multiple lines.$;
Print( "String with '$$' delimiter:\n", Multiline String, "\n" );
```

---

## Wrapper Functions

A function wrapper is a powerful pattern where a function takes another function as an argument and returns a new function. This new function "wraps" the original, adding behavior either before or after the original function is called.

### General Pattern

```slang
// The wrapper function takes another function as an argument
Wrapper Function = Func(
    Slang( Function To Wrap ),
    // ... other configuration arguments
)
Returns( Slang() ) // It returns a new function
{
    // ... logic to set up the wrapper's behavior (e.g., a cache)

    // Return a new function (often a Lambda) that "wraps" the original
    Return(
        Lambda( Ellipsis( Args ) )
        {
            // Behavior before calling the original function (e.g., check cache)
            // ...

            // Call the original function
            Result = @Function To Wrap( Args );

            // Behavior after calling the original function (e.g., store in cache)
            // ...

            Return( Result );
        }
    );
};
```

> **CRITICAL NOTE ON WRAPPERS:** When passing a function to a wrapper, you must pass the function variable itself, not the result of calling it.
>
> - **CORRECT:** `Wrapped Func = @Wrapper Function( My Function );`
> - **INCORRECT:** `Wrapped Func = @Wrapper ( @My Function );`

### Usage and Examples

**1. Original Function:** You start with a function that you want to wrap.

```slang
/****************************************************************
**  Routine: Private::Slow Fibonacci
**
**  Calculates the Nth Fibonacci number using a naive,
**  inefficient recursive approach. This function must be in a
**  non-local scope (e.g., Private::) to call itself.
****************************************************************/
Private::Slow Fibonacci = Func(
    Double( N )
)
Returns( Double() )
{
    If( N <= 1 )
    {
        Return( N );
    }
    :
    {
        // These recursive calls are computationally expensive for larger N.
        Return( @Private::Slow Fibonacci( N - 1 ) + @Private::Slow Fibonacci( N - 2 ) );
    };
};
```

**2. Wrapper Function:** You create a wrapper function that takes the original function as an argument and returns a new function with added behavior.

```slang
// A simple caching wrapper to speed up Fibonacci calculations
// Link the library containing the Memoize function
Link( "_LIB Cache Functions" );
// We pass the 'Private::Slow Fibonacci' function itself (without the '@' prefix)
// to the @Cache::Memoize wrapper. This returns a new, much faster function.
Fast Fibonacci = @Cache::Memoize( Private::Slow Fibonacci );
```

**3. Call the Wrapped Function:** You call the new function (`Fast Fibonacci`) just like the original.

```slang
Print( "Calculating Fibonacci(35) for the first time...\n" );
// The first call is slow as it computes and caches the results.
Result1 = @Fast Fibonacci( 35 );
Print( "Result: ", Result1, "\n\n" );

Print( "Calculating Fibonacci(35) for the second time...\n" );
// This second call is instantaneous because the result is retrieved from the cache
// instead of being re-calculated.
Result2 = @Fast Fibonacci( 35 );
Print( "Result: ", Result2, "\n" );
```

---

## Input and Output

- **Formatting:** `Format( NumericData, Width, Decimal, Flags )`.
- **Printing:** `Print`, `Printf`, `Sprint`, `Sprintf`, `PrintToFile`, `TeePrintToFile`, `PrintToObject`.

### Example

```slang
Formatted Value = Format( 1234.567, 10, 2, _Commas );
Print( "Formatted value: ", Formatted Value );

// Example demonstrating basic Sprintf usage
Name = "Elvis";
Age = 3;
Msg = Sprintf( "%s is %d years old", Name, Age );
Print( Msg ); // Output: Elvis is 3 years old
```

---

## Coding Style Guidelines

- Use a header comment block at the top of each script.
- Use function comment blocks for all functions.
- Use descriptive function and variable names.
- Variables should never be truly global variables. Minimize the use of global variables. Private variables are defined using `Private` keyword. ( e.g., `Private::My Variable = 5;` )
- Line length is restricted to 200 characters.
- Set tabs to 4 spaces.
- Use mixed case for function names, with spacing between logical words ( e.g., `My Function` instead of `MyFunction` ).
- Always prefer using spaces between logical words in variable and function names ( e.g., `My Function` instead of `MyFunction`, and `My Variable` instead of `MyVariable` ).

    ```slang
    /****************************************************************
    **  Routine: Private::My Function
    **
    **  Returns a constant value of 5.
    ****************************************************************/
    Private::My Function = Func(
    )
    Returns( Double() )
    {
        Return( 5 );
    };
    ```

- Function names should start with capital letters.
- Variable names should start with capital letters.
- Use mixed case for variables, with spacing between logical words ( e.g., `Expiration Date` ).
- Use named-scope variables only when defining functions in library scripts.
- Public functions in a library must be defined with library scope names. Private functions must be defined with `Private` scope.

### Example: Function Scoping in Libraries

```slang
/****************************************************************
**  Routine: Private::Size
**
**  This function returns the size of the argument.
****************************************************************/
Private::Size = Func(
    String( Argument ),
)
Return( Double() )
{
    Return( Size( Argument ) );
};

/****************************************************************
**  Routine: My Library::Function
**
**  This function returns the size of the argument.
****************************************************************/
My Library::Function = Func(
    String( Argument ),
)
Return( Double() )
{
    Return( @Private::Size( Arguments ) );
};
```

### Example: Multiple Return Types

```slang
// In Slang, functions can be designed to return different data types based on conditional logic.
// This is achieved using the 'Returns' keyword followed by a comma-separated list of possible
// return types. Within the function body, the 'Return' keyword is used to specify the actual
// value that is returned, and its type must match one of the types declared in the 'Returns'
// clause.

/****************************************************************
**  Routine: Private::Multiple Returns
**
**  Demonstrates a function with multiple return types.
****************************************************************/
Private::Multiple Returns = Func(
    Double( X ),
    Double( Y ),
)
Returns( Double(), Null )
{
    If( X > 0 )
    {
        Return( X + Y );
    }
    :
    {
        Return( Null );
    }
};

Result = @Private::Multiple Returns( 1, 2 );
Print( Result, "\n" ); // Should print 3

Result = @Private::Multiple Returns( -1, 2 );
Print( TypeOf( Result ), "\n" ); // Should print Null
```

---

## Typed Structures

- Typed Structures are user-defined data types with member variables and functions.
- Non-streamable Typed Structures are defined using the `TypeDefine()` function: `TypeDefine( "Namespace::Type Name" )`.
- Streamable Typed Structures are defined using the `TypeDefineStreamable()` function: `TypeDefineStreamable( TypeID, "Namespace::Type Name" )`.
- You can create an instance of a Typed Structure using the constructor. E.g., `Instance = Namespace::TypeName()`.
- If you create an instance of a Typed Structure or use the Typed Structure in a function signature and the Typed Structure is:
  - **Non-streamable**: You must link it in your script.
  - **Streamable**: You **DO NOT** need to link it in your script.
- `Msg New` is a function that is called during the construction of Typed Structures. The signature of `Msg New` can *only* be:
  ```slang
  Msg New = Func( Self )
  Returns()
  ```
  `Msg New` *does not* accept extra arguments. It only accepts `Self` as an argument, which represents the instance of the Typed Structure being constructed.
  This will not work as intended (accessing arguments other than `Self` inside `Msg New` will fail):
  ```slang
  Msg New = Func( Self, String( Invalid Extra Argument ) )
  Returns()
  ```
- Member functions of a Typed Structure instance are called using `.` operator ( e.g., `Instance = Namespace::TypeName(); Instance.Function();` ). Crucially, do *not* use `@` to call member functions of a Typed Structure.

### Full Typed Structure Example

```slang
// If you have any of the functions of the Typed Structure create new instances of the Typed
// Structure, you must forward declare the Typed Structure as follows:
TypeForward( "My Namespace::My Type" );
TypeDefine( "My Namespace::My Type" )
{
    // Constructor: it does not accept any arguments other than `Self`.
    // *DO NOT* add any other arguments to the constructor.
    Msg New = Func( Self )
    Returns()
    {
        Self.My Array = [ 1, 2, 3 ]; // Initialize My Array to an appropriate default
    };

    // Member function
    My Function = Func(
        Self,
        Double( Input Value ),
    )
    Returns( Double() )
    {
        Return( Input Value * Self.My Number );
    };

    // The members block must be the last block in the TypeDefine.
    Members()
    {
        // _RefCount enables reference counting for this typed structure.
        // This means instances are passed by reference, not by value,
        // which is essential for a linked list to function correctly
        // and manage memory efficiently.
        Double( _RefCount ),

        // Member variables can have default values
        Double( My Number ) := 0,
        String( My String ) := "",
        // Member variables without an explicit default value will be defaulted to a meaningful
        // value, e.g., Arrays will be defaulted to empty array.
        // If a field can't be defaulted to a meaningful value it will be initialized to Null.
        Array( My Array ),

        // For pointer- or reference-based data types, you can use `Any` so that you can
        // reset it to `Null` later. This is useful for linked lists, trees, or any other
        // data structure that requires references to other instances.
        // `Any` is a special type that can hold any value, including Null.
        // Avoid Typed Structures types if you want to set them to Null later.
        Any( Next ) := Null,
        Any( Previous ) := Null,

        // If a Typed Structure member is set to another value later, it *cannot* be
        // reset *back* to Null later. DO NOT do this with pointer-based data structures.
        My Namespace::My Type( Nested ) := Null, // Nested Typed Structure instance

        // Boolean member variable, use `TrueBool` and `FalseBool` for boolean values
        Boolean( Is Active ) := TrueBool,
        // Can serve as a boolean flag with `True` or `False` values.
        Double( Is Flagged ) := False,
    };
};

// Creating an instance of the Typed Structure
Instance = My Namespace::My Type();
// Member variables can be assigned upon creation of the instance
Another Instance = My Namespace::My Type( My Number := 1, My String := "foo" );

// Accessing member variables
Print( Instance.My Number, "\n" ); // Output: 0
// Assigning member variables
Instance.My Number = 10;
Instance.My String = "Hello";
Print( Instance.My Number, "\n" ); // Output: 10
Print( Instance.My String, "\n" ); // Output: Hello

// Calling a member function
Result = Instance.My Function( 5 ); // Result will be 50
Print( Result, "\n" ); // Output: 50

Instance.Next = My Namespace::My Type();
Instance.Next.My Number = 20;
Print( Instance.Next.My Number, "\n" ); // Output: 20
Instance.Next = Null;
Print( DataTypeOf( Instance.Next ), "\n" ); // Output: Null
```

- Must follow consistent indentation, variable naming, function naming, and bracket spacing.

---

## Summary

**Based on these guidelines, write Slang code that is well-formatted, readable, and efficient. Pay close attention to the specific requirements of each task and choose the appropriate data types, operators, and functions. Prioritize clarity and maintainability in your code.**
