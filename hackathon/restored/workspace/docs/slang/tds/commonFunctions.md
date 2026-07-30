# TDS Functions -- Quick Reference

A concise lookup of TDS (Tabular Data Set) functions in Slang. For detailed usage and patterns see `workingWithTds.md` and `examples.md`.

All functions below are **built-in** -- no `Link()` required.

---

## Schema Construction

| Function | Description |
|----------|-------------|
| `TdsSchema( names, types )` | Construct schema from column name and type arrays |
| `TdsSchema( names, types, primaryKey )` | Schema with primary key |
| `TdsDateSerSchema( names, types )` | Date-series schema (ID column is a date) |
| `TdsTimeSerSchema( names, types )` | Time-series schema (ID column is a time) |
| `TdsStructSchema( struct )` | Schema from a Structure or Typed Structure |
| `TdsSchemaIntersect( s1, s2 )` | Intersection of two schemas |
| `TdsSchemaUnion( s1, s2 )` | Union of two schemas |
| `TdsReadSchema( name, db )` | Read schema from disk |

---

## Schema Accessors

| Method | Description |
|--------|-------------|
| `schema.ColumnNames()` | Array of column names |
| `schema.ColumnTypes()` | Array of column type strings |
| `schema.ColumnSlangTypes()` | Array of Slang type strings |
| `schema.ColumnIndex( name )` | Column index by name |
| `schema.ColumnIndices( names )` | Array of column indices |
| `schema.ColumnType( name )` | TDS type string for a column |
| `schema.ColumnExists( name )` | True if column exists |
| `schema.PrimaryKey()` | Array of primary key column names |
| `schema.nCols()` | Number of columns |
| `schema.RowSize()` | Total row size in bytes |
| `schema.ColumnSize( name )` | Column size in bytes |
| `schema.isTimeSer()` | True if time series |
| `schema.isDateSer()` | True if date series |
| `schema.Description()` | Get/set schema description |
| `schema.toStructure()` | Schema as a Structure |

---

## TdsDataSet Construction

| Function | Description |
|----------|-------------|
| `TdsArray( data )` | Create from Array-of-Arrays, Array-of-Structures, or Structure-of-Arrays |
| `TdsArray( data, Schema := schema )` | Create with explicit schema |
| `TdsInMemory( schema )` | Empty in-memory TDS for row-by-row appending |
| `TdsFixedWindow( schema, nRows )` | Fixed-size in-memory TDS |
| `TdsDummyDataSet( schema, nRows )` | Generate dummy test data |
| `TdsCAlloc( schema, nRows )` | Allocate TDS in memory or temp file |

---

## TdsDataSet Properties

| Method | Description |
|--------|-------------|
| `tds.Size()` | Number of rows |
| `tds.nCols()` | Number of columns |
| `tds.IsEmpty()` | True if no rows (faster than `Size() == 0`) |
| `tds.schema()` | Returns the TdsSchema |
| `tds.isTimeSer()` | True if time series |
| `tds.isDateSer()` | True if date series |
| `tds.isStoredInMem()` | True if cached in memory |
| `tds.isStoredOnDisk()` | True if on disk |
| `tds.IsWritable()` | True if writable |
| `tds.IsSortedByPK()` | True if sorted by primary key |
| `tds.CheckSum()` | Checksum for comparison |
| `tds.Description()` | Get/set description |
| `tds.Pending()` | Pending lazy operations |

---

## Conversion -- TDS to Other Types

| Method | Description |
|--------|-------------|
| `tds.toArray()` | Array of Arrays (all columns) |
| `tds.toStructArray()` | Array of Structures |
| `tds.toStructCaseArray()` | Array of StructureCases |
| `tds.toStructOfArrays()` | Structure of Arrays |
| `tds.toGStructure()` | GStructure keyed by primary key |
| `tds.toColumnArray( colName )` | Single column as flat Array |
| `tds.toCurve()` | Curve from first column |
| `tds.toGCurve()` | GCurve |
| `tds.toRtCurve()` | RtCurve |
| `tds.toVector()` | Slang Vector |
| `tds.toMatrix()` | Slang Matrix |
| `tds.toNestedStructure( keys, leafCols )` | Nested Structure |

---

## Conversion -- Other Types to TDS

| Function | Description |
|----------|-------------|
| `TdsCurve( curve )` | Curve to TDS |
| `TdsGCurve( gcurve )` | GCurve to TDS |
| `TdsRtCurve( rtcurve )` | RtCurve to TDS |
| `TdsVector( vector )` | Vector to 1-column TDS |
| `TdsVectorRow( vector )` | Vector to 1-row TDS |
| `TdsMatrix( matrix )` | Matrix to TDS |
| `TdsToVector( tds )` | First column to Vector |
| `TdsToMatrix( tds )` | TDS to Matrix |

---

## Row Manipulation

| Function / Method | Description |
|-------------------|-------------|
| `tds.Append( arrayOrStruct )` | Append a row to writable TDS |
| `tds.Insert( arrayOrStruct, row )` | Insert row at position |
| `tds.InsertByPK( arrayOrStruct )` | Insert row sorted by primary key |
| `tds.Erase( rowNum )` | Erase row(s) |
| `tds.EraseByPK( keyVals )` | Erase by primary key |
| `tds.Rows( from, to )` | Extract row range |
| `TdsRange( tds, from, to )` | Same as `.Rows()` |
| `TdsTimeRange( tds, fromDate, toDate )` | Extract by date/time range |
| `TdsTop( tds, N, cols )` | Top N rows by column ranking |
| `TdsBottom( tds, N, cols )` | Bottom N rows |
| `TdsResetRowIDs( tds )` | Reset row IDs to sequential |

---

## Column Operations

| Function | Description |
|----------|-------------|
| `TdsExtend( tds, expr, colName, colType )` | Add column(s) |
| `TdsMap( tds, expr, colName, colType )` | Create single-column TDS |
| `TdsColumns( tds, colNames )` | Select columns (same as `TdsProject`) |
| `TdsProject( tds, colNames )` | Select columns |
| `TdsProjectAllBut( tds, colNames )` | Remove columns |
| `TdsColumnRange( tds, from, to )` | Columns by index range |
| `TdsRename( tds, oldNames, newNames )` | Rename columns |
| `TdsUniqColumns( tds )` | Remove duplicate column names |
| `TdsCommonColumns( arrayOfTds )` | Project to common columns |
| `TdsFold( tds, func, names, types, init )` | Custom fold/aggregation |

---

## Filtering and Restriction

| Function | Description |
|----------|-------------|
| `TdsRestrict( tds, lambda )` | Filter rows by boolean lambda |
| `tds.Restrict( lambda )` | Method syntax |
| `TdsWhere( tds, expr )` | SQL-like WHERE clause (string or lambda) |
| `TdsSelect( tds, colExprs, where )` | Combined SELECT + WHERE |
| `TdsUniq( tds, cols )` | Remove duplicate rows |

---

## Logical / Comparison Operators

All return a boolean TDS that can be used for indexing (`tds[ boolTds ]`).

| Function | Description |
|----------|-------------|
| `TdsEq( tds, val )` / `tds.Eq( val )` | Equal |
| `TdsNe( tds, val )` / `tds.Ne( val )` | Not equal |
| `TdsGt( tds, val )` / `tds.Gt( val )` | Greater than |
| `TdsGe( tds, val )` / `tds.Ge( val )` | Greater or equal |
| `TdsLt( tds, val )` / `tds.Lt( val )` | Less than |
| `TdsLe( tds, val )` / `tds.Le( val )` | Less or equal |
| `TdsNot( tds )` / `tds.Not()` | Logical NOT |
| `TdsAnd( a, b )` / `tds.And( b )` | Logical AND |
| `TdsOr( a, b )` / `tds.Or( b )` | Logical OR |
| `TdsIsNull( tds )` / `tds.IsNull()` | First column is null |
| `TdsIsNotNull( tds )` | First column is not null |
| `TdsIsAnyColNull( tds )` | Any column in row is null |
| `TdsRemoveNulls( tds )` | Remove rows with any null |
| `TdsIn( tds, array )` | Value is in set |
| `TdsBetween( tds, min, max )` | Value is in range |
| `TdsIf( boolTds, thenVal, elseVal )` | Conditional (ternary) |
| `TdsConst( value, tds )` | Constant TDS matching shape |

---

## Null Value Handling

| Function | Description |
|----------|-------------|
| `TdsFillFwd( tds )` / `tds.FillFwd()` | Fill nulls forward |
| `TdsReplaceNulls( tds, defaultValOrMap )` | Replace nulls with defaults |
| `TdsRemoveNulls( tds )` | Remove rows with any null |

---

## Key-based Search (Binary Search on Index)

| Function | Description |
|----------|-------------|
| `TdsKeyEq( tds, cols, vals )` | Rows where key == value |
| `TdsKeyGe( tds, cols, vals )` | Rows where key >= value |
| `TdsKeyGt( tds, cols, vals )` | Rows where key > value |
| `TdsKeyLt( tds, cols, vals )` | Rows where key < value |
| `TdsKeyLe( tds, cols, vals )` | Rows where key <= value |
| `TdsKeyRange( tds, cols, min, max )` | Rows where key in range |
| `TdsKeyIn( tds, cols, arrayOfVals )` | Rows where key in set |
| `tds.find( keyVals )` | Find row by primary key (returns TdsDataRow) |
| `tds.findRowNum( keyVals )` | Find row number by primary key |

---

## Sorting and Primary Keys

| Method / Function | Description |
|-------------------|-------------|
| `tds.PrimaryKey( cols )` | Set the primary key |
| `tds.SortByPK()` | Sort by primary key |
| `tds.Sort( cols )` | Sort by arbitrary columns |
| `tds.SortByFunc( func )` | Sort by custom function |
| `tds.IsSortedByPK()` | Check if sorted by PK |
| `tds.IsSortedBy( cols )` | Check if sorted by columns |

---

## Relational Joins

| Function | Description |
|----------|-------------|
| `TdsJoin( left, right, leftKey )` | Inner join |
| `TdsLeftJoin( left, right, leftKey )` | Left outer join |
| `TdsRightJoin( left, right, leftKey )` | Right outer join |
| `TdsUnionJoin( left, right, leftKey )` | Full outer join |
| `TdsMergeByKey( left, right, leftKey )` | Merge by key (union join + dedup columns) |
| `TdsSemiJoin( left, right, leftKey )` | Keep LHS rows with match in RHS |
| `TdsSemiMinus( left, right, leftKey )` | Keep LHS rows without match in RHS |
| `TdsDiff( left, right, key )` | Diff two datasets |
| `TdsDiffApply( left, diff, key )` | Apply a diff |

> All join functions accept optional `right_key` array for different key names.

---

## Aggregation and Grouping

| Function | Description |
|----------|-------------|
| `TdsGroupBy( tds, cols, output )` | GROUP BY with reduction operators |
| `TdsGroupByFunc( tds, cols, func )` | GROUP BY with custom Slang reduce function |
| `TdsCubeBy( tds, cols, output )` | Excel-style pivot table |
| `TdsRollupBy( tds, cols, output )` | Rollup pivot tree |
| `TdsCrossTab( tds, vKeys, hKeys, valCol )` | Cross-tabulation |

---

## Summary Statistics (Whole Dataset, Moving Window, or Cumulative)

All functions below have three modes:

1. **Whole dataset** (default): returns 1-row summary
2. **Moving window**: pass `window` parameter (date/time series only)
3. **Cumulative**: pass `cumul := 1` (date/time series only)

| Function | Description |
|----------|-------------|
| `TdsSum( tds, window, cumul )` | Sum |
| `TdsProd( tds, window, cumul )` | Product |
| `TdsAvg( tds, window, cumul )` | Average |
| `TdsMin( tds, window, cumul )` | Minimum |
| `TdsMax( tds, window, cumul )` | Maximum |
| `TdsFirst( tds, window )` | First value |
| `TdsLast( tds, window )` | Last value |
| `TdsVar( tds, window )` | Variance |
| `TdsStd( tds, window )` | Standard deviation |
| `TdsMedian( tds, window, cumul )` | Median |
| `TdsPercentile( tds, tile, window, cumul )` | Percentile (0-1) |
| `TdsMovAvgExp( tds, window )` | Exponential moving average |
| `TdsSummaryStats( tds )` | All summary stats in one pass |

---

## Row Statistics (Across Columns)

| Function | Description |
|----------|-------------|
| `TdsRowSum( tds )` | Sum across numeric columns per row |
| `TdsRowProd( tds )` | Product per row |
| `TdsRowAvg( tds )` | Average per row |
| `TdsRowMin( tds )` | Min per row |
| `TdsRowMax( tds )` | Max per row |
| `TdsRowVar( tds )` | Variance per row |
| `TdsRowStd( tds )` | Std deviation per row |
| `TdsRowMedian( tds )` | Median per row |

---

## Correlation, Covariance, Regression

| Function | Description |
|----------|-------------|
| `TdsCorr( x, y, window )` | Pearson correlation |
| `TdsCov( x, y, window )` | Covariance |
| `TdsDotProduct( x, y, window )` | Dot product |
| `TdsRegress( x, y, window )` | Linear regression (slope, intercept, R-squared) |
| `TdsCorrMatrix( tds, cols )` | Correlation matrix |
| `TdsCovMatrix( tds, cols )` | Covariance matrix |

---

## Time Series Operations

| Function | Description |
|----------|-------------|
| `TdsLag( tds, n )` | Lag by n rows |
| `TdsLead( tds, n )` | Lead by n rows |
| `TdsTimeSer( tds, colName )` | Move date/time column to ID |
| `TdsTimeSerToColumn( tds, colName )` | Move date/time ID back to column |
| `TdsTimeRange( tds, from, to )` | Extract date/time range |

---

## Arithmetic Operations

| Function | Description |
|----------|-------------|
| `TdsAdd( a, b )` | Element-wise add |
| `TdsSub( a, b )` | Subtract |
| `TdsMul( a, b )` | Multiply |
| `TdsDiv( a, b )` | Divide |
| `TdsMod( a, b )` | Modulo |
| `TdsPow( a, b )` | Power |
| `TdsRound( tds )` | Round |
| `TdsAbs( tds )` | Absolute value |
| `TdsSqrt( tds )` | Square root |
| `TdsExp( tds )` | Exponent |
| `TdsLog( tds )` | Natural logarithm |
| `TdsLog10( tds )` | Log base 10 |
| `TdsFloor( tds )` | Floor |
| `TdsCeil( tds )` | Ceiling |
| `TdsSign( tds )` | Sign |

---

## String Operations on TDS Columns

| Function | Description |
|----------|-------------|
| `TdsStrBegins( tds, prefix )` | StrBegins on all rows |
| `TdsStrEnds( tds, suffix )` | StrEnds on all rows |
| `TdsStrContains( tds, substr )` | StrContains on all rows |
| `TdsStrWildMatch( tds, pattern )` | Wildcard match on all rows |
| `TdsStrUpper( tds )` | Uppercase all string columns |
| `TdsStrLower( tds )` | Lowercase all string columns |
| `TdsStrRTrim( tds )` | Right-trim strings |
| `TdsStrLTrim( tds )` | Left-trim strings |
| `TdsSubStr( tds, start, len )` | Substring |
| `TdsStrReplace( tds, old, new )` | Replace all occurrences |
| `TdsRegExReplace( tds, regex, repl )` | Regex replace |
| `TdsStrLen( tds )` | String lengths |
| `TdsStrErase( tds, substr )` | Erase substring |

---

## Concatenation and Merging

| Function | Description |
|----------|-------------|
| `TdsConcat( arrayOfTds )` | Vertical concatenation (stack rows) |
| `TdsConcatByKey( arrayOfTds, cols )` | N-way merge by key (sorted) |
| `TdsConcatByPK( arrayOfTds )` | N-way merge by primary key |
| `TdsMerge( arrayOfTds )` | Horizontal merge by ID |
| `TdsZip( arrayOfTds )` | Horizontal merge (assumes aligned rows) |

---

## Column Type Conversion

| Function | Description |
|----------|-------------|
| `TdsConvert( tds, colName, colType )` | Convert single column type |
| `TdsConvertSchema( tds, newSchema )` | Convert all columns to new schema (positional) |
| `TdsMapToSchema( tds, newSchema )` | Map columns by name to new schema |

---

## Caching and Storage

| Function / Method | Description |
|-------------------|-------------|
| `tds.Cache()` | Cache entire TDS in memory |
| `TdsCache( tds )` | Materialize lazy TDS |
| `TdsTemp( tds )` | Save to temp file (auto-deleted) |

---

## File I/O

### TDS Binary Format

| Function | Description |
|----------|-------------|
| `TdsDB( path )` | Select a TDS database |
| `TdsRead( name, db )` | Read from disk |
| `TdsSave( tds, name, db )` | Save to disk |
| `TdsUpdate( name, db )` | Open for update |
| `TdsAppend( name, db )` | Open for append |
| `TdsWriter( name, db, schema )` | Create writer |
| `TdsDB::ls()` | List all tables in a database |
| `TdsDB::rm( name )` | Remove a table |

### CSV

| Function | Description |
|----------|-------------|
| `TdsCsvReadFile( file )` | Read CSV file to TDS |
| `TdsCsvReadStr( str )` | Read CSV string to TDS |
| `TdsCsvWriteFile( tds, file )` | Write TDS to CSV file |
| `TdsCsvWriteStr( tds )` | Write TDS to CSV string |

### Fixed Width

| Function | Description |
|----------|-------------|
| `TdsFWReadFile( file, colWidths )` | Read fixed-width file |
| `TdsFWReadStr( str, colWidths )` | Read fixed-width string |

### Parquet

| Function | Description |
|----------|-------------|
| `TdsToParquet( tds, name, db )` | Write to Parquet |
| `TdsToParquetBinary( tds )` | Convert to Parquet binary |
| `TdsFromParquet( name, db )` | Read from Parquet |
| `TdsFromParquetBinary( binary )` | Read from Parquet binary |

### Arrow IPC

| Function | Description |
|----------|-------------|
| `TdsPackToArrowIPCStream( tds )` | Convert to Arrow IPC stream |
| `TdsPackToArrowIPCFile( tds )` | Convert to Arrow IPC file |
| `TdsUnpackFromArrowIPCStream( binary )` | Read from Arrow IPC stream |
| `TdsUnpackFromArrowIPCFile( binary )` | Read from Arrow IPC file |

---

## Pivoting and Bucketing

| Function | Description |
|----------|-------------|
| `TdsDiscretize( tds, col, bounds )` | Bucketize column values |
| `TdsHistogram( tds, col, bins )` | Frequency distribution |
| `TdsDummyVars( tds, col )` | Create dummy/indicator variables |
| `TdsKeyValPairsToCols( tds, keyCols, valCol )` | Unpivot key-value pairs to columns |
| `TdsColsToKeyValPairs( tds, keyCols )` | Pivot columns to key-value pairs |

---

## Indexing

| Function | Description |
|----------|-------------|
| `TdsCreateIndex( tds, cols, db )` | Create an index |
| `TdsCreateBitmappedIndex( tds, cols, db )` | Create a bitmapped index |
| `TdsReadIndex( name, db, indexCols )` | Read through an index |
| `tds.HasIndex( cols )` | Check if index exists |

---

## Matrix Operations

| Function | Description |
|----------|-------------|
| `TdsMatrixMultiply( a, b )` | Matrix multiplication |
| `TdsMatrixTranspose( tds )` | Matrix transpose |
| `TdsMatrixInnerProduct( a, b )` | Inner product |
| `TdsMatrixTimesVector( a, b )` | Matrix-vector multiplication |

---

## Ranking

| Function | Description |
|----------|-------------|
| `TdsRank( tds )` | Rank values by column |
| `TdsPercentRank( tds )` | Percent rank by column |

---

## Tree Aggregation

| Function | Description |
|----------|-------------|
| `TdsTree( tds, pivotKeys, aggFuncs )` | Create a TdsTree |
| `TdsTreeRollup( tds, pivotKeys, aggFuncs )` | Create rollup tree |
| `tree.Value()` | TDS value for node |
| `tree.Child( n )` | Get nth child |
| `tree.NumChildren()` | Number of children |
| `tree.RawData()` | Unaggregated data for node |
