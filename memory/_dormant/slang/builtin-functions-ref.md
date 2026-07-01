---
created: 2026-04-14
updated: 2026-04-15
tags: [slang, builtins, functions, reference]
status: active
relates:
  - slang/builtin-functions.md
  - slang/language.md
---

# Slang Builtin Functions Reference

**609** curated builtins (of ~44,500). Use `FunctionInfo("Name")` for full signatures.

## Control Flow

- `Abort` — Abort current evaluation
- `AbortCheck` — Block; check for abort every N seconds (0=always, <0=never, default=1)
- `AbortTrapEscape` — Block; trap and suppress abort signals
- `AbortTrapInteractive` → Double — Block; trap abort interactively. Returns True if abort was trapped
- `Break` — Exit innermost loop
- `Case` — See `Typecase()` for usage; used inside Switch constructs
- `Catch` — Exception type filter clause; see `Try()` for syntax
- `Check` — Throw if `!Expression`; optional error expression
- `CheckE` — Throw if `IsError(Expression)`; see also `CheckN()`
- `CheckN` — Throw if `Expression == Null`; see also `CheckE()`
- `Continue` — Skip to next iteration of innermost loop
- `Do` — SlangQL query block header
- `DoGlobal` — Execute block in global scope
- `Each` — Also multi-case in Switch
- `Error` — Error value
- `Finally` — Language construct for guaranteed cleanup after Try block
- `FirstNonError` — Return first non-error argument; infix form: `Or Else`
- `For` — C-style for loop
- `ForChildren` — Traverse children of a graph node matching criteria
- `ForComponent` — Iterate over keys of a container (Structure, etc.)
- `ForComponentValue` — Alias for ForEachComponent — iterates (key, value) pairs
- `ForEach` — Iterate over elements; use `&Var` for modifiable reference
- `ForEachComponent` — Iterate over (key, value) pairs of a container
- `ForSecurity` — Iterate over all securities of a given class: `ForSecurity( Instance, "Eq Index State" ) { Print( Security Name( Instance ) ); };`. The loop variable is a **security handle**, not a name string.
- `If` — Conditional branch: `If(cond) { ... } : { ... };`
- `Or` — Short-circuit logical OR; requires at least 1 argument
- `Or Else` — Infix form of `FirstNonError`: `A Or Else B` returns first non-error value
- `Return` — value from current function
- `Scope` — Access a variable by name from a named scope or call depth
- `Switch` — Pattern match: `Switch(Val, Match1, Op1, ..., [Default])`. Use `Each([...])` for multi-case
- `Throw` — Throw an exception with object, error code, and node
- `Try` — Exception handling: `Try(ex) { ... } : Catch(Type(v)) { ... } : { default };`
- `When` — Conditional guard clause
- `Where` — Filter clause inside a SlangQL `Do` block
- `While` — Loop while condition is true
- `With` — Context manager block (like Python `with`). Enter/Exit functions called automatically

## Functions & Compilation

- `Apply` — Call a function with positional array and optional named args
- `AtExit` — Register a function to run when evaluation ends
- `AtParseTime` — Execute a block at parse time (for tests/examples; avoid in production scripts)
- `CFunc` — C function reference
- `Closure` — Attach the current environment as a closure to a Slang function
- `CompilerPragma` — Parse-time compiler directive placeholder (no runtime effect)
- `CurrentFunctionName` — name of the currently executing function
- `CurrentModuleName` — name of the currently executing module/script
- `DispatchedFunctionArgs` — Block; declare arguments for a dispatched function using `SlangArg(...)`
- `DispatchedFunctionUsage` → String — Set the usage text for a dispatched function (shown by FunctionInfo)
- `Ellipsis` — Variadic argument placeholder (use `Ellipsis(_)` in stubs to match any args)
- `Foldl` → * — Left fold (reduce): apply `f(acc, elem)` across list `l` starting from `init`
- `Func` — Declare a function: `Func(a, b=1, c:=2) { ... }`. Params: `Var` or `Type(Var)`
- `FunctionInfo` → * — Metadata for function (args, return type, usage text)
- `Functions` → Array — List all function names
- `Lambda` — Anonymous function (same syntax as `Func` but captures closure automatically)
- `LintPragma` — Parse-time lint suppression marker (no runtime effect)
- `Mapcar` — Apply function to corresponding elements of one or more arrays
- `Returns` — Parse-time return type declaration for a function

## Type System

- `Any` — Type constructor for Any (matches all types)
- `Array` — Array
- `Boolean` — Boolean
- `DataTypeInfo` — Metadata for datatype
- `DataTypeOf` → String — datatype name of an expression
- `DataTypes` — List all registered datatype names
- `Date` — Date
- `Defined` — Test whether expression evaluates without error
- `Double` — Double
- `GsDt` — Wrap value as GsDt (Double/String/Array/Vector)
- `IsError` — Test whether a value is an Error
- `IsKindOf` → Double — True if base class of Derived equals BaseType
- `IsKindOfDtName` — Check type inheritance by datatype name strings
- `Null` — Parse-time Null literal
- `Security` — Security reference
- `Slang` — Slang code object
- `String` — String
- `Structure` — Structure from tag/value pairs
- `TypeDefinePackage` — Parse-time: define a typed structure package
- `TypeInfo` — Metadata for type; omit name to list all loaded types
- `TypeName` → String — type name of a datatype instance
- `TypeOf` → String — type name of an expression

## Type Conversion & Formatting

- `Asc` → Double — Return ASCII code of the first character in String
- `BinFromBase64` → Binary — Decode a Base64 string to Binary
- `BinToBase32` → String — Base32-encode a Binary
- `BinToBase64` → String — Base64-encode a Binary
- `Chr` → String — Convert ASCII code to a single-character String
- `Crc16` → Double — CRC-16-ANSI checksum of Binary
- `Crc32` → Double — CRC-32-IEEE checksum of Binary
- `Format` — Format data for display with width, decimal precision, and flags
- `Printf` — C-style formatted print to stdout (like Sprintf but prints instead of returning)
- `Sprint` → String — Like Print but returns the output as a string instead of printing
- `Sprintf` — C-style string formatting (`%d`, `%g`, `%s`, etc.)

## Math

- `Abs` — Absolute value
- `ArcCos` — Inverse cosine
- `ArcSin` — Inverse sine
- `ArcTan` — Inverse tangent
- `Arg` — Argument (phase angle) of complex number
- `Average` — Arithmetic mean of array/vector; optional column mode
- `Ceil` — Round up to nearest integer
- `Conj` — Complex conjugate
- `Cos` — Cosine (radians)
- `Cosh` — Hyperbolic cosine
- `CumNorm` — Cumulative normal distribution function
- `CumNormInv` — Inverse of cumulative normal distribution
- `DAvg` → GsDt — Distributional average with parameters
- `Exp` — Exponential (e^x)
- `Floor` — Round down to nearest integer
- `Interp` — String interpolation: replace `${name}` with values from Vars structure
- `Interpolate` — Interpolate a curve at given date(s) using specified method
- `Log` — Natural logarithm (ln)
- `Log10` — Base-10 logarithm
- `Max` — Maximum of two or more values
- `Min` — Minimum of two or more values
- `Mod` — Modulo (remainder of x/y)
- `N_BrentMin` — Find minimum of `ArgFunc(x, Context)` in [Low, High] using Brent's method
- `N_BrentRoot` — Find root where `ArgFunc(x, Context) = RHS` in [Low, High] using Brent's method
- `Pow` — Power: x raised to y
- `Random` → Double — Uniform random deviate (0,1). Pass NEGATIVE seed to initialize; positive ignored
- `RandomGauss` — Gaussian random deviate; optional seed
- `RandomReseed` → Double — Reseed Random with any Double/Date/Time/Int32 (non-negative seeds not ignored)
- `Round` — Round to specified decimal precision
- `Sign` — Sign: -1, 0, or 1
- `Sin` — Sine (radians)
- `Sinh` — Hyperbolic sine
- `Sqrt` — Square root
- `Stats` — Compute statistics on a Vector or Array of numeric data
- `Sum` → * — Sum values of Array/Vector/GsDtVector/GStructure; optional initial value. Uses `+=` accumulation
- `Tan` — Tangent (radians)
- `Tanh` — Hyperbolic tangent

## Array

- `Array2DToStruct` → Structure — Convert `[[a,b],[a,c]]` string arrays to Structure counting occurrences
- `Array3DToStruct` → Structure — Convert 3D string arrays to nested Structure counting occurrences
- `ArrayAgg` — Aggregate into array (SlangQL `Do` block only)
- `ArrayCartesianProduct` → Array — Cartesian product of two arrays
- `ArrayConcat` — Concatenate arrays; optional Index in Array1 for insertion, Count elements from Array2. Call-by-value
- `ArrayConcatAgg` — Concatenation aggregate (SlangQL `Do` block only)
- `ArrayConvert` → Double — Convert a GsDt array value
- `ArrayDelete` — Delete element(s) from array at given position
- `ArrayExtract` — Extract a subarray starting at Index for Count elements
- `ArrayInitialize` → Array — Create array of n elements initialized to elem_value
- `ArrayInsert` — Insert element(s) into array at given position
- `ArrayReverse` — new array with elements in reverse order
- `ArrayTranspose` → Array — Transpose an array of arrays; first element's size determines result size
- `ArrayUnique` — Remove duplicates in-place (LValue). Expects sorted input unless SortItFirst=True. Returns count removed
- `ArrayValidate` — Validate all elements match required base Datatype
- `Bsearch` — Binary search sorted array; returns Null if not found. Optional inexact match and comparator
- `Concat` — Concatenation operator (SlangQL `Do` block only)
- `Contains Value` — True if Container has Value; supports predicate, comparator, binary search
- `Each` — Also multi-case in Switch
- `FindSubArray` → Double — Find position of SearchFor subarray within SearchIn (KMP algorithm)
- `Join` — Relational join (SlangQL `Do` block only)
- `Lsearch` — Linear search container; returns Null if not found. Supports element match or predicate
- `Sort` — Sort Array/Vector/GsDtVector in-place. Comparator returns <0/0/>0. Default: stable merge sort
- `TableInit` — Create array of Structures from `[[tags...], [row1...], ..., [rowN...]]` array

## String (Str*)

- `Left` → String — Left-justify data in field of given width
- `RegEx` — compiled regular expression object
- `RegExP` → RegEx — Compile PCRE (Perl-compatible) regex; optional Flags (e.g. REG_ICASE)
- `RegMatch` → * — Match compiled regex against String; returns Array of captures or Null
- `RegMatchAll` → Array — Find all matches of compiled regex in String; returns Array of match arrays
- `RegSub` → * — Regex substitution: replace matches in Source using Template. REPL_GLOBAL for all
- `Right` → String — Right-justify data in field of given width
- `StrBegins` → Double — True if String starts with SubString
- `StrChrCount` → Double — Count characters from CharSet in String
- `StrCmp` → Double — Case-sensitive cmp: <0, 0, or >0
- `StrContains` → Double — True if String contains SubString (equiv. `StrPos >= 0`)
- `StrEnds` → Double — True if String ends with SubString
- `StrEscape` → String — Escape special (non-alphanumeric) characters
- `StrField` → String — Get the Nth field from a delimited string
- `StrFieldOld` → String — Legacy version of StrField; get Nth field from delimited string
- `StrFromBase64` → String — Decode Base64 to String
- `StrFromHtml` → String — Decode HTML entities to plain text
- `StrFromPrice` → String — Format a numeric price value as string
- `StrHash` — Hash a string to an integer value
- `StrHeight` → Double — Number of lines in a multi-line string
- `StrICmp` → Double — Case-insensitive cmp: <0, 0, or >0
- `StrJoin` — Join array elements with Glue separator
- `StrJustify` — Justify string within given width
- `StrLower` → String — Convert to lower case
- `StrMixCase` → String — Capitalize first char of each word
- `StrNCmp` → Double — Case-sensitive cmp of first N chars
- `StrNICmp` → Double — Case-insensitive cmp of first N chars
- `StrPos` → Double — Find first position of SubString in String (-1 if not found)
- `StrRepeat` → String — Repeat String n times
- `StrReplace` → * — Replace substring/regex. Flags: REPL_GLOBAL, REPL_CASE (case-sensitive). Supports PCRE
- `StrSplit` → * — Split string by delimiter; optional blank filtering
- `StrSplitCsv` — Split CSV-formatted string (handles quoting)
- `StrToBase64` — Encode String as Base64
- `StrToHtml` → String — Encode string for HTML/URL display
- `StrToPrice` → Double — Parse a price string to numeric value
- `StrTranslate` — Character-by-character translation (like Unix tr)
- `StrUpper` → String — Convert to upper case
- `StrWidth` → Double — Max line width of a multi-line string
- `SubStr` — Extract substring by start/end offset
- `Trim` → String — Remove leading/trailing whitespace

## Structure

- `CaseInsenStringValueStructure` — case-insensitive string-keyed, string-valued Structure
- `ComponentEnsure` — Get component Key (LValue); create with InitialValue if missing. InitialValue lazily evaluated
- `ComponentExists` — True if Tag exists in Container; see also `ComponentExistsStrict`
- `ComponentExistsStrict` — True if Tag exists in Container; redboxes if Container is invalid
- `ComponentExtract` — Return Tag's value if it exists, else DefaultValue. See also `ComponentExtractStrict`
- `ComponentExtractStrict` — Like ComponentExtract but redboxes if Container is invalid
- `ComponentGetStrict` — If Tag exists: set Var, return True. If not: set Var to DefaultValue, return False. Redboxes on invalid Container
- `ComponentReplace` — Replace component Key of Container with Value (LValue)
- `ComponentTestAndGet` — Same as ComponentGetStrict but no redbox on invalid Container
- `ComponentValueStructure` — ComponentValueStructure (key-value pair)
- `ContractMembers` — Declare contract members inside `TypeDefinePackage()` only
- `DtStructureKeyCaseSet` → * — Set the canonical casing of a Structure key
- `GStructure` — global-key Structure (case-insensitive keys)
- `GStructureFromKeys` — Create GStructure from parallel arrays of keys and values
- `StringValueStructure` — string-keyed, string-valued Structure
- `StructureCase` — case-sensitive Structure
- `StructureCaseFromKeys` — Create StructureCase from parallel key/value arrays
- `StructureFilter` → * — Return copy of Input with matching values removed; Tolerance for Double range
- `StructureFromKeys` — Create Structure from parallel key/value arrays
- `StructureRedimension` → * — Rearrange Structure components into a new order
- `StructureStatistics` — Return memory usage statistics for a Structure
- `StructureUnion` — Merge Src into Dest (LValue): add missing keys from Src; existing keys unchanged

## Hash

- `HashCaseKeys` — Return StructureCase of global case-sensitive Structure keys
- `HashFunc` → Double — Case-insensitive 32-bit hash of a string
- `HashKeys` — Return Structure of global (case-insensitive) Structure keys
- `HashPortable` → Double — Portable 32-bit hash of Value; Mode is HASH_MODE_FLAGS
- `HashQuick` — Fast non-portable hash code (for session-local hash tables only)

## TDS (Tabular Data)

- `TdsAdd` → GsDt — Element-wise ADD: TDS+scalar, TDS+single-col, or TDS+TDS (matching schemas). Also `+` operator
- `TdsAnd` → GsDt — Logical AND of two boolean TDS
- `TdsAppend` → GsDt — TdsWriter to append rows to an existing TDS file
- `TdsArray` → GsDt — Create TDS from array-of-arrays, array-of-structures, or structure-of-arrays
- `TdsAvg` → GsDt — Average: full aggregate (1 row), moving window, or cumulative
- `TdsBetween` → GsDt — Test if each value is within [min, max] range
- `TdsBottom` → GsDt — Bottom N rows ranked by specified columns
- `TdsCeil` → GsDt — Element-wise ceil of numeric columns
- `TdsColsToKeyValPairs` → GsDt — Unpivot: convert columns into key/value pairs. Inverse of TdsKeyValPairsToCols
- `TdsColToId` → GsDt — Move a sorted Numeric/Date/Time column into the TDS ID
- `TdsColumns` → GsDt — Select a subset of columns by name/index
- `TdsCommonColumns` → Array — Return array of TDS trimmed to only shared columns
- `TdsConcat` → GsDt — Concatenate an array of TdsDataSets (no key merge)
- `TdsConcatByKey` → GsDt — N-way merge an array of TDS by specified key columns
- `TdsConst` → GsDt — Broadcast a constant as a TDS matching arg's shape
- `TdsDiff` → GsDt — Diff two TDS by key columns; returns differences
- `TdsDiv` → GsDt — Element-wise DIVIDE. Also `/` operator
- `TdsFillFwd` → GsDt — Fill Null values forward in time series
- `TdsFloor` → GsDt — Element-wise floor of numeric columns
- `TdsGetMaxBinaryBuf` — global max binary buffer size setting
- `TdsJoin` → GsDt — Inner join two TDS on specified key columns
- `TdsMapToSchema` → GsDt — Map TDS to new schema by column name; drops/adds columns; converts types
- `TdsMod` → GsDt — Element-wise MODULO
- `TdsMovAvgExp` → GsDt — Exponential moving average over numeric columns
- `TdsMul` → GsDt — Element-wise MULTIPLY. Also `*` operator
- `TdsNot` → GsDt — Logical NOT of a boolean TDS
- `TdsOr` → GsDt — Logical OR of two boolean TDS
- `TdsProject` → GsDt — Project (select) columns — same as TdsColumns
- `TdsRead` — Read a TdsDataSet from disk
- `TdsReplicateRow` → GsDt — Replicate a 1-row TDS to match all rows of another TDS
- `TdsRestrict` → GsDt — Filter rows by a Slang boolean function
- `TdsRound` → GsDt — Element-wise round: TDS to scalar precision or TDS-TDS
- `TdsRowColValue` → GsDt — Index into TDS using a row/column index dataset
- `TdsSave` — Save a TdsDataSet to disk
- `TdsSaveAsColumns` → Double — Save TDS as separate per-column files
- `TdsSchema` → GsDt — Construct TdsSchema from arrays of names, types, and primary key names
- `TdsSelect` → GsDt — Select computed columns with optional where clause
- `TdsSqrt` → GsDt — Element-wise square root of numeric columns
- `TdsStrBegins` → GsDt — StrBegins applied row-wise across two TDS or TDS vs scalar
- `TdsStrReplace` → GsDt — Replace pattern in all string columns
- `TdsStrRTrim` → GsDt — Right-trim all string columns
- `TdsSub` → GsDt — Element-wise SUBTRACT: TDS-scalar or TDS-TDS. Also `-` operator
- `TdsSum` → GsDt — Sum: full aggregate (1 row), moving window, or cumulative
- `TdsTop` → GsDt — Top N rows ranked by specified columns
- `TdsTransform` → GsDt — Transform TDS rows via Slang function into new columns
- `TdsWhere` → GsDt — Filter rows by Slang where clause (string or lambda); can use PK/indexes

## Curve

- `Curve` — Curve (Date/Value pairs). Subscript by Date, Double index, or String. Access `.Values` / `.Dates`
- `CurveAdd` — Add two curves element-wise using interpolation Method
- `CurveBlend` — Blend array of curves; Callback(Date, ArrayOfValues) called per unique date
- `CurveCompress` → Binary — Msgpack-compress a Curve to Binary
- `CurveDeepSum` — Sum all values of a GCurve or GTCurve (recursive sum)
- `CurveDefiniteIntegral` → Double — Analytical definite integral of Curve between lower and upper index
- `CurveDeleteKnot` — Delete knot(s) from (G)Curve by Date or index
- `CurveDifference` — Return knots from Curve1 whose dates are not in Curve2
- `CurveDivide` — Divide two curves element-wise using interpolation Method
- `CurveExcludeByRank` — Delete knots by rank; positive=largest, negative=smallest
- `CurveExtremeLocations` — Find extreme value locations in Curve within optional index range
- `CurveFind` — Binary search for Date in Curve/TCurve/GCurve; returns index or -1 if not found
- `CurveFromDates` — Create Curve from array of dates with uniform Value (default 1.0)
- `CurveFromDatesUnique` — Like CurveFromDates but removes duplicate dates
- `CurveIntersection` — Return Curve with dates present in both; values from Curve1
- `CurveIntRateFromFwd` — Convert forward rate curve to interest rate at Date
- `CurveIntRateToFwd` — Convert interest rate curve to forward rate at Date
- `CurveMax` — Return maximum of all values in Curve/TCurve/RTCurve
- `CurveMaxMin` — Element-wise max or min of two curves (or curve and scalar). Type: `Max` or `Min`
- `CurveMerge` — Merge: use CurveB between Start/EndDate, CurveA outside
- `CurveMin` — Return minimum of all values in Curve/TCurve/RTCurve
- `CurveMultiply` — Multiply two curves element-wise using interpolation Method
- `CurveRange` — Extract date range subset from Curve/TCurve/RtCurve/GCurve
- `CurveSearch` — Binary search: return knot index <= Date; -1 if below lowest date
- `CurveShift` — Shift all Curve dates by RDate with optional holiday calendars
- `CurveShiftGS` — Shift Curve dates by RDate (GS variant, no explicit calendars)
- `CurveSubCurve` — Extract subcurve of Size knots starting at Index
- `CurveSubtract` — Subtract two curves element-wise using interpolation Method
- `CurveSum` — Return sum of all values in Curve/TCurve
- `CurveSwitches` — Return switch points of a Curve
- `CurveTermVolFromFwdVol` — Convert forward volatility curve to term volatility at Date
- `CurveToTCurve` — Convert Curve to TCurve with optional time-of-day and timezone
- `CurveToVectors` — Convert Curve to date/value vectors relative to BaseDate
- `CurveUncompress` → * — Msgpack-decompress Binary back to Curve
- `CurveUnion` — Union of two curves; Curve1 knots take priority on overlap
- `CurveZap` — Remove knots within Epsilon of Value (default 0). Acts as zap-zeros by default
- `GCurve` — GCurve (grouped curve with string keys mapping to sub-curves)
- `RCurve` — RCurve (RDate/Value pairs). Subscript by RDate, Double index, or String. `.Values`/`.Dates` accessors
- `RCurveToCurve` — Convert RCurve to Curve by resolving RDates relative to Date with holiday calendars

## Dialog

- `Dialog` — Base dialog function (requires SecView)
- `DialogAskMktData` — Prompt user to select a market data security
- `DialogAskMultilineText` — Prompt user for multi-line text input (requires SecView)
- `DialogAskPassword` — Prompt user for password input (requires SecView)
- `DialogAskSecPick` — Security picker dialog (requires SecView)
- `DialogAskStrTab` — String table selector dialog (requires SecView)
- `DialogAskText` — Prompt user for single-line text input (requires SecView)
- `DialogAskYesNo` → Double — Ask yes/no question; returns 1=Yes, 0=No/Escape
- `DialogAskYesNoCancel` → Double — Ask yes/no/cancel; returns 1=Yes, 0=No, -1=Cancel/Escape
- `DialogEdit` — Open security edit dialog (requires SecView)
- `DialogEnableSUIT` — Block; enable SUIT dialog drive for dubwin
- `DialogFieldGet` — Get dialog field by index array
- `DialogFieldGetValue` — Get the value of a dialog field
- `DialogFieldGoto` — Navigate to a dialog field
- `DialogFieldHide` — Hide or show a dialog field
- `DialogFieldSet` — Set dialog field values from Structure
- `DialogFieldSetState` — Set the state of a dialog field
- `DialogFieldSetValue` — Set the value of a dialog field; optional Initial flag
- `DialogMakeAvailable` — Block; make SecView available in the executed block
- `DialogRecalc` — Recalculate a dialog
- `DialogUpdateStrTab` — Update string table in dialog (requires SecView)

## Diddle / Overrides

- `DiddleList` — List diddles for a security; pass Null for all diddles
- `DiddleListDb` — Convert diddle scope to array; optional streamable inference
- `DiddleListNew` → * — Get diddle list for a specific node, security, or database
- `DiddleScope` — DiddleScope value
- `DiddleScopeDefine` — Block; define diddle scope in which diddles are applied
- `DiddleScopeList` — DiddleScopeList value
- `DiddleScopeTemporaryGet` — current temporary diddle scope
- `DiddleScopeUse` — Block; use specified diddle scope; optional apply to intermediates
- `Restore` — Restore diddled values; no args = restore all, or specify VTs/securities
- `RestoreDiddle` — Restore diddles; no args = restore all, or specify VTs/securities
- `SetDiddle` — Override (diddle) a value method. Also: `SetDiddle(VTName, Sec, Value, Flags)`
- `SetDiddleRestoreFirst` — Restore then SetDiddle; workaround for phantom diddle bug
- `SetDiddleWithArgs` — Diddle a VT with dynamic argument list. Use SetDiddle for no-args case
- `StickyDiddle` — Block; diddles set within block persist after block exits

## Error Handling (Err*)

- `Err` → Double — Set LastError to ErrorText, LastErrorNumber to ErrorCode; returns False
- `ErrB` — Set error text (B severity variant)
- `ErrClear` — Clear the error state
- `ErrD` — Set error text (D severity variant)
- `ErrE` — Set error text (E severity variant)
- `ErrLevelGet` — Get the current error reporting level
- `ErrLevelSet` — Set error reporting level (controls ErrMsgHookFunc calls)
- `ErrMore` → Double — Append ErrorText to LastError; returns False
- `ErrMoreB` — Append error text (B severity variant)
- `ErrMoreD` — Append error text (D severity variant)
- `ErrMoreE` — Append error text (E severity variant)
- `ErrMoreN` — Append error text (N severity variant)
- `ErrMoreR` → Error Result — Append error text and return LastErrorResult
- `ErrN` — Set error text (N severity variant)
- `ErrOff` → * — Block; evaluate with errors turned off (for debugging)
- `ErrR` → Error Result — Set error and return LastErrorResult
- `LastError` — text of the last error
- `LastErrorNumber` — numeric code of the last error
- `LastErrorResult` → Error Result — Return Error Result from LastErrorNumber, LastError, and optional Context
- `LastSevereError` — text of the last severe error
- `LastSevereErrorNumber` — numeric code of the last severe error
- `LastSevereErrorResult` → Error Result — Return Error Result from LastSevereErrorNumber, LastSevereError, and Context

## Enum

- `EnumNames` — Return array of member names for a given enum
- `Enums` — List all registered enum names
- `EnumScope` — Parse-time: define a scoped enum `EnumScope(Name){ Const1 [= Value], ... }`
- `GetEnumValue` → Double — numeric constant for an enum value's string representation

## Index

- `IndexDescriptor` → * — Return index descriptor structure for specified ID, or Null
- `IndexGet` — Retrieve from index by position and get-type
- `IndexGetByName` — Retrieve from index by name, get-type, and security name
- `IndexGetByNameMany` → Array — Batch retrieve from index for multiple security names
- `IndexInfo` — Info on an index
- `IndexIteratorBatchSize` — Block; override batch size used by SecDbIndexIterator
- `IndexNames` — Return array of the current database's index names
- `IndexPosSecurity` — security at a given index position

## I/O & Files

- `ClipboardRead` — Read text from system clipboard
- `ClipboardReadUTF8` → * — Read clipboard as UTF-8 encoded Binary
- `ClipboardWrite` — Write object/text to system clipboard
- `DiskInstreamValues` → Structure — Return structure of instream VT names → values for a security
- `DiskInstreamValuesMany` — Batch version of DiskInstreamValues for multiple securities
- `File` — File datatype
- `FileCopy` — Copy a file (no wildcards)
- `FileCreate` — Create a new file (optionally with FileName or Null)
- `FileDelete` — Delete a file
- `FileExists` — True if file exists
- `FileFlush` — Flush buffered data for a File object
- `FileFreeSpace` — Return free disk space for root path
- `FileMove` — Move a file (no wildcards); optional move flags
- `FileNormalize` — Expand `%VAR%` in filename using env/filemap.dat
- `FileOpen` — Open file; default READ+WRITE. Use FILE_OPEN_READ for read-only. Magic names: stdin, stdout, stderr
- `FileOptions` — Get/set file options (e.g. FILE_OPTION_NON_BLOCK). Omit Options to query
- `FileOwner` → String — owner of a file
- `FileReadBinary` — Read up to Size bytes as Binary; Null on error, zero-length Binary if non-blocking and no data
- `FileReadLine` — Read one line from a File
- `FileRegisterForCleanup` — Register file for automatic cleanup at exit
- `FileRename` — Rename a file (no wildcards)
- `FileReopen` — Redirect stdout/stderr to a file; use with caution
- `FileRunCleanupFunc` — Run registered file cleanup functions
- `FileSearch` — Search for file in directory searchpath (default PATH)
- `FileSeek` — Set position in file; optional FromEnd flag
- `FileShortPath` — Convert filename to short (8.3) path form
- `FileStat` → * — Return file info: Size, Type, Times, Readable, Writable, Executable
- `FileTell` — Return current position in file
- `FileTempName` — Generate temp filename; optional auto-cleanup at exit
- `FileTruncate` — Truncate file to specified length
- `FileUnRegisterForCleanup` — Unregister file from automatic cleanup
- `FileWrite` — Write data to a file
- `Print` — Print one or more values to stdout
- `PrintToFile` — Block; redirect Print output to a file
- `PrintToObject` — Block; redirect Print output to an object
- `ReadFromFileStream` → * — Deserialize an object from a file stream
- `StreamByRef` → * — Stream a value by reference
- `StreamSize` → Double — Return binary stream size of a value
- `WriteToFileStream` → Double — Serialize an object to a file stream

## Date & Time

- `AddDate` — Offset a Date by days/months/years with optional business day rules
- `AllowNegativeDates` — Enable/disable negative (pre-epoch) dates
- `CurrentGMTime` — Return current GMT time; optional re-sync
- `CurrentTime` — Return current local time
- `CurrentTimestamp` — Return SDB::Timestamp for current UTC time
- `Date` — Date
- `DateFromMDY` — Construct Date from month, day, year
- `DatePart` — Extract component: `Year`, `Month`, `Day`, `Y`, `M`, `D`, etc.
- `DateTime` — DateTime
- `HolidayIsHoliday` → Double — Returns 1 (holiday), 0 (business day), or -1 (no calendar found)
- `RDate` — relative date (e.g. `1m`, `2y`, `3bd`)
- `RDateAdd` — Add relative date to absolute date with holiday calendar support
- `RDateIsDate` — True if the RDate represents a concrete (absolute) date
- `TimeFromDate` — Convert Date to Time with optional timezone, hour, minute, second
- `TimeFromDateNew` — Convert Date to Time (new version); default timezone is GMT
- `TimeGmtToLocal` — Convert GMT time to local time in specified timezone
- `TimeLocalToGmt` — Convert local time to GMT; optional timezone
- `Today` — Return today's date
- `Weekday` — Return day of week (0=Sunday .. 6=Saturday)

## SecDB Core

- `Attributes` — Typed-structure member attributes; follow a member declaration in Members()
- `BookDealLookup` → * — Find existing Deal Info security name for Book + ExternalTradeID, or Null
- `BookDealName` → String — Compute Deal Info name from Book + ExternalTradeID using hash scheme
- `BookDealUnpack` → Structure — Unpack a Deal Info incremental transaction part into components
- `ClassInfo` — Metadata for class; set Load=False to skip loading
- `ClassInfoByID` — Metadata for class by numeric ID
- `CLex` — Lex (tokenize) a Slang code string with LEX_* flags
- `CLink` — Link a C function from DLL by path and name
- `Database` — Database reference
- `DatabaseDuplicate` — Create a duplicate database handle with separate cache
- `DatabaseErrorLogContents` — Read from database error log (nBytes from Offset)
- `DatabaseErrorLogSize` — Return size of database error log
- `DatabaseStack` — Return array of UseDatabase stack (innermost first)
- `DatabaseUpdate` — Flush pending updates to database
- `DatabaseUsers` — List users connected to the database
- `DatabaseUtilization` — Return database utilization statistics
- `DealSink` — Deal sink for trade processing
- `DefineClass` — Block; define a security class with its value type table
- `DefineClassNonStreamable` — Block; define a non-streamable class
- `Destroy` — Destroy variables; `Destroy(NULL)` destroys all
- `DtProfile` — Block; profile DT_MSG calls up to Max Depth
- `DtPropertyInfoByName` → * — Look up a datatype property by name
- `DtPropertyInfoByVal` → * — Look up a datatype property by value
- `Edit Info` — Edit Info value
- `Eval` — Block; evaluate a block and return result
- `Exec` — Execute a string or Slang code object at runtime
- `GetValue` — Evaluate a value method on a security
- `GetValueError` — error from the last GetValue call (dispatched from _LIB UFO Rules Fns)
- `GetValueWithArgs` — Evaluate a value method on a security with additional arguments
- `Link` — Parse-time: link a Slang script (makes its functions available)
- `LoginName` — Return login name of current user
- `New` → * — Allocate a new instance of datatype TypeName
- `ReloadSecurity` — Reload security from disk; pass Null to reload all
- `SecViewAvailable` — True if SecView UI is available
- `SecViewIsSafe` — Get/set SecView safe mode; optional Safe flag to set
- `SetValue` — Set a value method's value; Flags: SDB_SET_INTERACTIVE or 0
- `SetValueRef` — Block; modify a value method's value by reference via OutVar
- `SetValueWithArgs` — Set a value method with additional arguments
- `Show` — Display a value in a debug viewer
- `ShowSecurity` — Display security in SecView window

## Binary & Encoding

- `Binary` — Binary
- `BinaryExtract` → * — Extract a byte range from a Binary
- `BinaryFromInt32` → Binary — Convert a 32-bit integer to Binary
- `BinaryToInt32` → Double — Convert Binary to 32-bit integer
- `BinaryV2` → * — Convert to Binary with string interning enabled
- `BUnzip2` → * — Bunzip2-decompress a Binary; returns Null on failure
- `CanonicalBinary` → Binary — Canonical binary image of Value (securities streamed by value, not name)
- `CheckSum` — Compute checksum of a security
- `CompressZstd` → * — Zstd-compress a Binary; returns Null on failure
- `ConvertFromStreamingFormat` → * — Deserialize from a streaming format to a typed structure
- `ConvertToStreamingFormat` → * — Serialize a typed structure to a streaming format
- `Crypt` — Unix-style crypt hash
- `DataPack` → * — Pack Structure data into binary using format descriptors
- `DataPackFormats` — Return all available DataPack format descriptors
- `DataPackMany` → * — Pack array of structures into binary
- `DataUnpack` → * — Extract record from Binary per format. Returns Structure (default) or Array
- `DataUnpackMany` → * — Extract multiple records from Binary

## Debugging & System

- `AddUncaughtExceptionHandler` — Register a global uncaught exception handler
- `Breakpoint` — Trigger a debugger breakpoint
- `BreakpointToggle` — Programmatically toggle a breakpoint at a source location
- `CallStack` — current call stack (optional detail level)
- `ConnectionDelete` — Delete a database connection
- `ConnectionInfo` → * — Return details for a database connection (0=aggregate stats)
- `CPPException` — Throw a C++ exception of specified type (for testing)
- `CPUFeatures` — Return structure of available CPU feature flags
- `CPUInfo` — Return CPU information for current machine
- `CPUUsage` — Return overall CPU usage percentage
- `Debug` — Enter interactive debugger
- `DebugAssert` — Assert all expressions return True
- `DebugBreak` — Set a data breakpoint on a variable
- `DebugLevel` — Set debug verbosity level
- `DebugMessage` — Output message to attached debugger (Windows only)
- `DFDictionary` — Load a DF dictionary by name/version/revision
- `DFDictionaryNewest` — Load newest DF dictionary where revision >= specified
- `DFEngine` — Create a DF (Data Flow) engine
- `DFLogRetrieveAndClearText` — Retrieve and clear DF log text
- `DFLogRetrieveText` — Retrieve DF log text
- `DFService` — Create a DF service endpoint
- `DFShutdown` — Shut down a DF session
- `DFStart` — Start a DF session
- `DiskInfo` → * — Return on-disk metadata for a security
- `DiskInfoMany` → Array — Batch DiskInfo for multiple securities
- `HeapInfo` — Return heap memory usage statistics
- `Sleep` — Pause execution for sleepTime seconds
- `System` — Execute an OS shell command

## Constants

- `Constant` — Parse-time: define a named constant
- `ConstantInfo` — Metadata for constant
- `Constants` — List constants; optional prefix filter and detail flag
- `ConstantValue` — runtime value of a named constant

## Collections & Bits

- `BitAnd` — Bitwise AND
- `BitNot` — Bitwise NOT
- `BitOr` — Bitwise OR
- `BitVector` — bit vector
- `BitXOr` — Bitwise XOR
- `CMatrix` — complex matrix
- `CVector` — complex vector
- `Deque` — double-ended queue
- `Matrix` — numeric matrix
- `Socket` — network socket
- `Trie` — trie (prefix tree)
- `Vector` — numeric Vector from values, or `Vector(Count)` for sized
- `WeakRef` — weak reference

## Misc

- `Back` → * — Return last element of Value (array/string); Offset from end (default 0)
- `BackSolve` → GsDt — Solve AX=B where A is triangular
- `BrentRootFinder` → GsDt — Find root of Function in [Low, High] using Brent's method
- `Center` → String — Center-justify data in field of given width
- `CGXLongOperation` — Block; wrap a long operation with UI progress feedback
- `DlgCreate` — Create a dialog widget
- `DlgHourglass` — Block; show hourglass cursor during execution
- `DlgMsg` — Send a synchronous message to a dialog widget
- `DlgMsgPost` — Post an async message to a dialog widget
- `IgnoreValue` — Ignore return value of a function call (suppresses lint warnings)

## Serialization (JSON/XML)

- `jsonify` → String — Serialize Slang value to JSON string
- `ToXml` — Serialize value to XML string
- `unjsonify` → * — Parse JSON string to Slang value (Array or StructureCase)

## Database & Security

- `DeleteSecurity` — Delete security from database
- `DiskRecord` — Return raw disk record for a security; flags control detail level
- `EditSecurity` — Open security for editing (requires SecView)
- `GetSecurity` → * — Retrieve security from database/cache. Flags: SDB_REFRESH_CACHE, SDB_CACHE_ONLY, SDB_IGNORE_PATH
- `RenameSecurity` — Rename a security; Null name to infer via inference rules
- `SecDbNew` → * — Create new instance: `SecDbNew(ClassName)` or `SecDb::ClassName()`
- `SecurityAdd` — Add a security from a structure of values
- `SecurityAddByInference` — Add security by inference from values
- `SecurityCopy` — Copy security between databases
- `SecurityDuplicate` — Duplicate instream values from Source to Target
- `SecurityIsNew` — True if security has not yet been written to database
- `Transaction` — Block; execute within a database transaction
- `TransactionAbort` — Abort current transaction; optional error text (calls ErrMore) and error code (calls Err)
- `UpdateSecurity` — Write security to database (no validation)
- `UseDatabase` → * — Block; push database onto stack, execute block, pop. Returns block result
- `UseDatabaseForClasses` — Block; execute in appropriate RW database for class home ring
- `Validate` — Run security validation programmatically
- `ValidateSecurity` — Validate security; display warnings/errors in window
- `ValidateSecurityWithReturnFlags` — Validate security; returns -1 for abort, else validation flags
- `ValidSecurityName` → Double — True if SecName is a valid security name

## Environment & System

- `EnvGet` → * — Get environment variable value; returns Null if not set. Case-sensitive on Linux
- `EnvGetAll` — Return StructureCase of all environment variables
- `Exit` — Stop evaluation and return value to OS
- `GetEnv` → * — Get environment variable; omit arg for all env vars
- `GetHostByAddress` — DNS reverse lookup: IP address to hostname
- `GetHostByName` — DNS forward lookup: hostname to IP address
- `HostName` — Return current hostname
- `MemoryUsage` — Return memory usage statistics
- `ProcessID` — Return current process ID
- `ProcessInfo` — Return structure with count of all/running/sleeping processes
- `ProcessIsActive` → Double — True if process PID is active and belongs to same user
- `ProcessKill` — Send kill signal to process PID
- `Profile` — Profile a script and write timing output to FileName
- `PutEnv` → Double — Set environment variable: `PutEnv("NAME=value")`. Local to current process
- `SetConsoleTitle` — Set the console window title
- `SetUserName` → String — Get/set SecDb username; optional credentials for SecureDb connections
- `Size` — Return length/size of a value (array, string, structure, etc.)
- `SourceDatabase` — current Source Database of the SecView session
- `SplashScreenHide` — Hide the splash screen
- `SplashScreenMessage` → Double — Update splash screen message text
- `SplashScreenShow` → Double — Show splash screen for application with optional message and on-top flag
- `ToStringMaxSize` → Double — Get/set max string size for Array/Structure toString conversion
- `UseOle` — Block; CoInitializeEx, execute block, CoUninitialize

## Trade

- `TradeAdd` — Add a trade from a structure of values
- `TradeDelete` — Delete a trade by name
- `TradeDuplicate` — Duplicate a trade (optionally rename)
- `TradeInsertRaw` — Insert raw binary trade data into database
- `TradeIsPriorDay` — True if trade is from a prior day
- `TradeModifyPriorDay` — Mark modified trade as prior-day modified
- `TradePetCreationDisabled` — Block; disable PET creation within block
- `TradePositionEffectsUpdateDisabled` — Block; disable position effects update within block
- `TradeSimulation` — Block; use simulation trade IDs for new trades
- `TradeTypeGetOppositeType` — Get the opposite trade type
- `TradeTypeIsOpeningType` — True if trade type is an opening type
- `TradeUpdate` — Modify values of an existing trade

## TSDB (Time Series)

- `Tsdb` — Evaluate a TSDB expression; optional start/end date range
- `TsdbFunc` — Call a TSDB function by name with start/end dates and arguments
- `TsdbFuncHelp` — Return help text for a TSDB function
- `TsdbFuncRT` — Call a TSDB real-time function by name with start/end dates
- `TsdbFuncs` — List all available TSDB function names
- `TsdbGetModifiers` — Return modifiers for a TSDB symbol
- `TsdbGetSymbolData` — Batch fetch TSDB data for array of symbol names
- `TsdbLastPoint` — Return last data point for a TSDB symbol
- `TsdbLastPointCache` — Set the TSDB last-point cache size
- `TsdbLastValue` — last value of a TSDB expression
- `TsdbSymbolCreate` — Create a new TSDB symbol
