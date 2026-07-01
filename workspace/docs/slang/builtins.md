
GSLogo	
SLAM - The Slang Manual
slang
SLAM Links
SLAM Home
SLAM Indices
Full Index
Scope Index
Full Scope Index
Name Index
Library Index
Type Index
Addin Index

Example Index
Config Index
SLAM Docs Index

SLAM FAQ
SLAM Learning Path

Search FAQs: 
Search SLAM: 
Useful Links
FAQ Main
Technical Documents
Learning Paths

Contents 
Debug
Control Flow
Error Handling
Function Definition
Mush
Encryption
System
Link
Indexes
Buffer
Pack
Output
Cache
Databases
Securities
Excel
Structures
Transaction
Types
Description
Interface
Debug
DebugAssert	Evaluates all expressions which must return TRUEDebug level is currently 'on'.
RmDir	Removes a directory specified in Directory.
DynaLinkGetVersion	The DynaLinkGetVersion function retrieves version data about a specific Dll.
DynaLinkIsLoaded	Determines if a dll is currently loaded.
DynaLinkGetConfig	Retrieves data from the 'DynaLink.
Control Flow
ForEach	Iterates through every element in an enumerable datatype (e.
ForChildren	Given a starting node, this function traverses the children of the given node, ...
ForChildrenMultiSet	Similar to ForChildren with 2 major differences - accepts input set of nodes on ...
ForSecurity	Iterates through a list of all securities in the database that belong to a ...
ForIndex	Iterates through an index from a specified starting position.
ForValue	Iterates through all the VTs for a given security (Sec).
ForClass	Iterates through all classes in SecDb.
SecDbGraphHash	Computes a hash of the shape of the graph below Root, based on VT names & class ...
Break	Aborts the flow of the current LoopExample For(i = 0; i < 10 ; i++) { ...
Continue	Skips to the next iteration in a loop.
Exit	Stops the current Slang evaluation and returns ReturnValue.
Abort	Simulates a press of the Abort key.
AbortTrap	DEPRECATED
For	Executes a looped conditional expression.
Switch	Executes a matched conditional expression.
AbortCheck	Specifies how frequently SecDb polls for an abort action (e.
Lambda	Lambda is essentially an expression that returns a function.
Closure	DEPRECATED - Use @Lambda
Error Handling
Error	A constructor for the Error datatype (and takes no arguments).
RedboxSuppress	Evaluates the enclosed block, suppressing redboxes.
ForFile	Iterates through all files specified in FileSpec in the current directory.
Function Definition
Return	Terminates execution of the function in which it appears and returns control ...
Returns	Function signature indicating one or more datatype that the function returns If ...
Finally	A Finally block at the end of a @Func block is executed either when the function ...
Throw	An exception is an occurrence that causes a program to stop executing its normal ...
Mush
GobMushInStreamValues	Returns a 32-bit hash value of SecPtr's instream values passed in ChildData ...
GobMushString	Create a string using secdb name friendly characters from a mush value.
GobMushStringToDouble	Create a mush string from a string.
Encryption
System
HeapInfo	Returns a Structure containing information about allocated memory.
ProcessFork	Standard Unix fork
ProcessWait	Waits for the Process attached to Process ID to terminate before continuing with ...
ProcessKill	Kills the process that is associated with PIDExample //Kill self.
ProcessCpuTime	Retrives the actual CPU time used by slang session A Double is returned ...
ProcessAffinityMaskSet	Sets affinity mask for this process .
ProcessDirectoryGet	Fetches contents of Win32 shared memory block with given name
ProcessDirectoryPut	Copies data into Win32 shared memory block with given name
ProcessDirectoryLock	Acquires exclusive lock on named Win32 shared memory segment.
ProcessDirectoryUnlock	Releases exclusive lock on named Win32 shared memory segment.
Link
SmartLink	Parses SmartLinkEnabled libraries at run-time.
Include	Includes and evaluates the contents of another script.
EvaluateSuperLinkedScript	Includes and evaluates the given named script much like Include, but ...
CurrentModuleName	Returns the name of the Current Script.
Indexes
NewIndexPos	NewIndexPos is used to create a new Index Pos Index datatype.
IndexPosSecurity	Retriveves the item/data stored from a Index Pos Index datatype.
IndexGetByName	Retriveves the item/data stored in a Index.
IndexGet	Retrieve data from an indexReturnsName of object matching get operationThe ...
IndexNames	Returns an array of index names.
IndexInfo	Returns information about an Index.
IndexRepair	When IndexName is not provided: Repairs SecName in secdb database indexes, by ...
Buffer
OutputBufferNew	Clear the output buffer and set a new title if supplied
OutputBufferBrowse	Allow user to browse though the output buffer.
OutputBufferSave	Save the contents of the current output buffer.
OutputBufferSetFore	no description
OutputBufferSetBack	Sets the foreground for the output buffer
Pack
BinaryFromInt32	Convert binary from Int 32.Example x = BinaryFromInt32( 5 ); // x= 2
BinaryToInt32	Convert binary to Int 32.
Output
PageAt	This function puts text into a Page datatype.
PageBox	Draws lines on the boundry of the Page datatype which is defined by the ...
Printf	Writes FormatString to the current print handler replacing format specifiers ...
Sprintf	Like C's sprintf function, this function takes a format string and replaces its ...
Cache
CachedSecurities	Retrieve a list of cached securities (including those with reference counts of ...
SecDbLiteralLruCache	Returns a list of literal nodes in the LRU cache as a SecDb Node.
SecDbLiteralLruCacheFlush	Removes all literal nodes from the LRU cache.
Databases
InfiniteTransLogDb	Returns the infinite transaction log database for the provided Database ...
SourceDatabaseSet	Sets the sourcedatabase to NewSourceDb(Name), and returns the new Source ...
Securities
GetUniqueID	Returns a unique number.
ClassInfo	Get the class information for the named class.
ClassInfoByID	Get the class information for the named class.
ClearLoadHistory	Clears the TrackLoad log.
TrackLoadHistory	Enables the TrackLoad code to log successful SecDB object gets in a list ...
TrackLoadHook	Enables the TrackLoad code to send a log of successful SecDB object gets to a ...
TrackLoadCallDepth	Sets the height of the call stack saved by TrackLoad.
SetTrackLoadHook	Sets callback to call for successful object gets in TrackLoad.
GetLoadHistory	Returns TrackLoad log about object gets.
ConfigurationGet	Returns a the value ( which could be a String or Double) of the Name specified ...
GetUserCredentials	Get the user credentials for Secure Database connections.
LoginName	Retrives LoginName
DbIOSuppressByImplementation	This function suppresses database i/o within the bound block for all dbs with ...
DbIOSuppressedByImplementation	Returns true if I/O is suppressed for this class of db SEE ALSO: ...
SecurityAdd	Adds an instance of a specified Security to the database.
SecurityAddByInference	Creates an instance of an object class containing the Implied Name VT.
SecurityUpdate	Like UpdateSecurity, SecurityUpdate also takes an object (or the name of an ...
SecurityDuplicate	Copies data from Source security and assigns the same values to Target security.
DeadpoolSecurities	Returns a structure of all securities in the current root db deadpool.
SecurityIsEqual	Returns TRUE if Sec1 and Sec2 are equal.
SecurityIsNew	Returns True if the DateCreated VT in SecPtr does not have an assigned value.
DeleteSecurity	Removes a Security from the database and returns True if the security was ...
DeleteSecurityDuringConflict	UsageThis addin can only be called by script "_LIB Analyze Conflicts"ExampleSee ...
RenameSecurity	Renames the OldSecurity to NewName and returns True if the Object was ...
ReloadSecurity	Reloads Sec object and refreshes it from the database.
ExistsInDatabase	Queries the database to see if a Security (defined by Security Name) exists in ...
NameLookup	Finds object names in the database based on a search criteria.
GetByInference	Retrieves or creates a security by inferring it's existence If the object ...
NewSecurity	Returns a new security of security type SecType with the name specified in ...
GetSecurityFromSyncPoint	Retrieves a previous version of a security.
UpdateSecurity	Updates a security in the database or creates a new security if the security is ...
SecDbInsertSecurityRaw	Inserts a transaction given a binary of the security
SecDbCopyNoLoad	Copies an object, as the name suggests, without loading it, by copying the ...
SecDbCopyNoLoadPreservePageTable	Copies an object, as the name suggests, without loading it, by copying the ...
SecDbRestoreNoLoad	Copies a security in binary form from translog or syncpoint.
InferredName	Inferred names are essentially hash codes that allow SecDb to quickly identify ...
SecDbNewLoad	Load the object specific information for a new security from an ...
RemoveFromDeadPool	Removes an unreferenced object, or all unreferenced objects from the deadpool ...
AllowSecurityUpdateOnTrade	DEPRECATED Use the functions in Trade APIs to create/update/delete trades so ...
Validate	Validates a Securityby determining if an object considers itself to be valid.
ValidateVT	Validates a vt of a security.
InvalidateValue	Clear a Set-Retained value from a security
InvalidateValueIfNotDiddled	Clear a Set-Retained value from a security
GetValue	Returns a value from the object.
GetValueWithArgs	Gets a value for a security.
SetValue	Sets a value of a Security.
SetValueWithArgs	Set the value of security VT's that are defined SetRetain (typically those ...
SetDiddle	Diddle values (given in ValueMethodName) within a Security.
ValueTypeDescription	Returns security valuetype descriptionExample SecName = "TestValueTypeDesc"; ...
ValueTypeInfo	Returns global Info about a value type, such as it's Datatype and the ID which ...
ValueTypeChildInfo	Returns a structure containing valuetype information of the Child ...
WhiteoutDiddle	Restores the diddle on this node and all sideffects (if it is a phantom) to the ...
GetCacheFlags	Returns a double (cache flags) for Value Method for a given SecurityExample ...
SetValueRef	An alternate way to set the value of a VTExample sec = NewSecurity( "foo" ); // ...
SecDbGraphClearFailures	Clears the cached failures on the specified node and its failed descendants.
SecDbBuildChildren	Builds the first-level children of a given node. Throws on error.
SecDbBuildFullGraph	Builds the full graph starting from a given root node and ensures that it is ...
Excel
CellAttrRange	Sets the attributes for a range of cells in a sheet.
CellFontRange	Sets the font information for a range of cells in a sheet.
CellFormatRange	Sets the format within a range of cells in a spreadsheet.
SheetBox	Draws a box around a group of cells in Sheet.
SheetColumnWidth	This function sets the width of a column in a sheet.
SheetRowHeight	Sets the height of Row in Sheet.
SheetPostscript	Outputs a sheet in postscript format by converting a sheet datatype into ...
SheetToFile	Converts Sheet to a txt file specified by Destination.
Apply	Evaluates the input function with the parameters provided.
StatusMessageHook	For Debugging
SlangUninitializedVarHook	For Debugging
SlangExpressionGet	Retrives the script specified in Script Name as a string.
SlangExpressionOverride	Overides a script expression with the new expression specified.
CallStack	Returns an array of all scope names.
GetExecutionContexts	Returns an array of Call Stacks, one for each active execution context.
SlangCallStackAllThreads	Returns an array of Call Stacks, one for each Slang thread.
SecDbGetNodeStack	Returns the current SecDb Node Stack (for debugging)
CurrentFunctionName	Returns the name of the current slang function.
Scope	Returns a reference to variable within scope.
Variables	Retrieves a list of variables within the scope provided by ScopeName.
SlangPosition	Returns info on the current cursor position.
Structures
ForComponent	Iterates through all the keys (components) in a Structure, GStructure, or Typed ...
ComponentExists	Searches Container and checks whether the key defined by Tag resides in the ...
ComponentExistsStrict	Similar to ComponentExists.
ComponentTestAndGet	Allows users to access the value associated to the the key Tag within a ...
ComponentGetStrict	Similar to ComponentTestAndGet, allows users to access the value associated to ...
ComponentExtract	Allows users to access the value associated to the the key Tag within a ...
ComponentExtractStrict	Similar to ComponentExtract.
ComponentEnsure	Returns component Key of Container (as an Lvalue if needed); if the component ...
ComponentReplace	Replaces the component Key of Container with Value.
ForComponentValue	Iterates through all the keys (components) in a Structure, GStructure, or Typed ...
StructureFromKeys	Creates a datatype of Structure/StructureCase from a list of keys and values ...
GStructureFromKeys	Creates a datatype of GStructure from a list of keys and values specified in ...
Structure	A Structure is a datatype that stores many pairs of keys and values.
StructureStatistics	Returns statistics about the memory usage of InputStruct.
SysNCon	System() without creating a console window on Windows
System	Executes an operating system Command that is passed in.
AccessViolate	This will bring up the just-in-time debugger.
CPPException	Throws a C++ exception of the specified CPP_EXCEPTION_TYPE for testing the ...
SlangXProcessDieWithParent	Controls whether this process will die when its parent process goes away; ...
Shutdown	System call to shut down a computer.
ShowStack	Prints out the current state of stack.
ThreadID	no description
Transaction
TransLogLast	Retrieve the number of the last transaction in the database.
TransLogHeader	Retrieve the header associated with a transaction.
TransLogDetail	Any time a database is modified (something added, deleted, modified, index ...
TransLogObjects	no description
TransLogSecTypes	Return an Array of the security types of the securities modified by transaction, ...
TransactionCurrent	Get current uncommitted transactionThe optional Memory Dump Flag argument ...
TransactionSize	Return size of binary in current uncommitted transaction
Transaction	This function is used to ensure that all database operations within a block ...
TelemetryTransaction	TelemetryTransaction provides a facility for composing telemetry transactions.
TransactionAsync	TransactionAsync() can be used in place of Transaction()when you need to commit ...
TransactionCommit	Commits and starts a transaction if the current transaction exceeds Parts ...
TransactionAbort	Aborts a Transaction that is in progress
TransMap	Returns the current server's transaction map
Types
TypeForward	Registers a type structure at parse-time, and links it with a dummy message ...
TypeDefine	Constructor for defining a non-streamable type.
TypeDefineInterface	Define an interface.
TypeDefinePackage	Define a Typed Structure Package.
TypeDeclare	Defines a streamable type.
TypeInfo	Returns structure of info for the type.
TypeInfoByID	Returns structure of info for the type id.
TypeUndefine	no description
TypeLink	Registers a streamable typed structure, and makes it available globally.
TypeLinkDeprecated	no description
Op	no description
SlangXWinProcessCreate	no description
SlangXWinProcessExitCode	no description
SlangXWinProcessJoin	no description
Debug Top
DebugAssert = Func(	src search usage feedback   top
Slang( Expression )
// Slang Expression
) Returns( )
Evaluates all expressions which must return TRUE Debug level is currently 'on'. In the example below, the debuuger will kick in since m == 3 will evaluate to FALSE
Example
 m = 4;
 DebugAssert(m == 3);
RmDir = Func(	src search usage feedback   top
String( Directory )
// Directory to change remove
) Returns( Double )
Removes a directory specified in Directory. Only empty directories can be removed.
Returns
True - Directory removed without error
False - Directory not found, or couldn't be removed
See Also
MkDir, ChDir
DynaLinkGetVersion = Func(	src search usage feedback   top
String( Dll )
// Dll name (w/o .dll)
) Returns( Structure )
The DynaLinkGetVersion function retrieves version data about a specific Dll. The structure returned has the following components:

Name	Description
Area	Build region (core, strat, V... )
CompileNumber	Number of the compiler.
CompileTime	Time the dll was linked.
Major	Major revision number.
Message	Text informational comment.
Minor	Minor revision number.
Name	Name of the dll (with extension.)
Version	Text version number.
Example
 Print(DynaLinkGetVersion("eqspnumericss"));
Output
Area         : bld/pre
CompileNumber: 17
CompileTime  : Wed 31Jan07 06:45:03 pm
major        : 2
Message      : Compiled on Wed Jan 31 18:45:03 2007
minor        : 3
Name         : eqspnumericss.dll
Version      : 2.3.17
DynaLinkIsLoaded = Func(	src search usage feedback   top
String( Dll )
// Dll name (w/o .dll)
) Returns( Double )
Determines if a dll is currently loaded.
Returns
True - Dll is currently loaded.
False - Dll is not currently loaded.
DynaLinkGetConfig = Func(	src search usage feedback   top
) Returns( Array )
Retrieves data from the 'DynaLink.cfg' file. The information is returned in an array of structures. The structures have the following components:

Name	Description
Allowed	Array of structures defined below.
DllLoadPath	Actual path of dll. This is only set if
the dll is currently loaded.
DllName	Name of dll (without path or extension.)
The Allowed structures have the following components:


Name	Description
Area	Build region (core, strat, V... )
CompileHigh	Highest allowable compile value.
CompileLow	Lowest allowable compile value.
MajorHigh	Major revision highest allowable value.
MajorLow	Major revision lowest allowable value.
MinorHigh	Used, bad idea.
MinorLow	Used, bad idea.
Example
 Print(DynaLinkGetConfig())
Output
[   0] = Allowed    :
[   0] = Area       : bld/pre
CompileHigh: 17
CompileLow : 17
MajorHigh  : 2
MajorLow   : 2
MinorHigh  : 3
MinorLow   : 3

DllLoadPath:
DllName    : eqspnumericss
state      : Not_Checked

[   1] = Allowed    :
[   0] = Area       : bld/pre
CompileHigh: 18
CompileLow : 18
MajorHigh  : 2
MajorLow   : 2
MinorHigh  : 3
MinorLow   : 3

DllLoadPath:
DllName    : corba_utils
state      : Not_Checked
Control Flow Top
ForEach = Func(	src search usage feedback   top
*( Element ),
// Loop variable, use &Var to get a modifyable reference.
*( Container )
// An enumerable datatype. Element will be set to each value in the Container
) Returns( )
Iterates through every element in an enumerable datatype (e.g. , Array, Structure, Curve, GStructure, etc..). During each iteration, the element at the current iteration index of Container is copied to Element. This allows the user to access the current value directly. It is also the same as defining Element = Array[ i ] inside a For loop.
When the & operator is used with Element, any modifications to Element during iteration will be reflected on the enumerable value. The followimg example iterates through an Array and prints the contents of an Array. The second example iterates through a Curve and modifies the value. Please use the code with caution since the second example modifies an existing curve.

You can optionally use a datatype or datatype+spec on the iterator variable: see Slang Specs: How do I establish preconditions and postconditions on function arguments and return values?

Example
 //Print the name of each object in the array
 ObjNames =
 [
      "DEM/USD",
      "JPY/USD",
      "CHF/USD",
      "ITL/USD"
 ];

 ForEach( ObjName, ObjNames )
 {
      Print( ObjName, "\n" );
 };

 // And now with datatype+spec
 ForEach( String( ObjName, Spec::String( Max Size := 31 ) ), ObjNames )
 {
      Print( ObjName, "\n" );
 };

 // Square all of the values in a curve.
 // Note that a Reference to each element is created by using & and the squared value is stored
 Curve = Volatility Curve( "USD/DEM" );
 ForEach( &Knot, Curve )
 {
      Knot.Value *= Knot.Value;
 };
See Also
ForComponent , Array
ForChildren = Func(	src search usage feedback   top
*( Child ),
// Loop variable
Any( ValueMethod ),
// Root VT expression or Value Reference()/Secdb Node.ValueReference()
Any( SecTypeFilter ),
// Either a String Security/Interface type or a NodeFilter instance
Any( ValueTypeFilter ),
// For String SecType arg, ValueType name/array of names. Else optional traversal filter
Any( Flags )
// Double or Structure( "Flags", Flags {, "ObjectRegEx", RegEx } )
) Returns( )
Given a starting node, this function traverses the children of the given node, iterating over nodes found matching specified criteria. The graph is built as needed, but values are not calculated unless required to determine the topology of the graph.
Parameters
Child
A Loop variable that holds a information about the current child. This information is a Structure and contains the following attributes:


Attribute Name	Description
Name	Name of the current node.
Args	Arguments for the current node.
Node	SecdbNode representating the current node.
Value Type	Value type of the current node.
ValueMethod
Starting node of the graph to be searched. This may be a currently invalid node, in which case ForChildren will build the graph as it traverses. (Note this does not apply to Value References -- see below.)
Node expressions may be used. Invalid (uncalculated) expressions enable ForChildren to partially build your graph.

 Price( "Option" )
Value References, which are pointers to fully calculated nodes with valid values, can be provided as root nodes.

 Value Reference( "Price", "Option" )
 SecDb Node( Price( "Option" ) ).ValueReference()
Expressions can also be programmatically created.

 Node = SecDb Node( Price( "Option" ) )
 VTApply = VTApply( ArrayConcat( [ Node.ValueType.Value ], Mapcar( \x -> x.Value, Node.Args ) ) );
 Security = Node.Object.Value
 ( VTApply )( Security )
SecTypeFilter and ValueFilter
These two arguments define the matching criteria for located nodes.

SecTypeFilter	ValueFilter	Filter
Null	Null	All nodes.
String	Null	Nodes on securities of given security type.
Null	String or Array	Nodes on any security with given VT name(s).
String	String or Array	Nodes on given security type with given VT name(s).
NodeFilter	Any (ignored)	Nodes matched with NodeFilter functions (see F4).
NodeFilter	NodeFilter	Nodes matched with filter and second arg traversal filter.
Flags
The flags specify the depth or level of the traversal. For example, specifing _TREE will traverse the node recursively ( enumerating the children of that node). The default behaviour ( Null ) is the same as specifing _TREE. Certain flags (i.e _Prune ) are only useful if SecType or ValueFilter is specified since they only stop at those nodes. They do not traverse nodes that evaluate to false for criteria specified in SecType and ValueFilter.
Flags are alsp additive, i.e you can combine one or more flags. Regex... The following enumeration flags are supported:

Flags	Description
_First Level	Enumerate only the immediate children.
_Tree	Descend down the tree and enumerate all of the children.
_Leaves Only	Enumerate only the bottom-most children.
_External	Enumerate children that are flagged as external.
_Prune	Prune the tree for the condition specified in SecType and ValueFilter.
_Sorted	Sort the returned values in reverse order by ( VT Name, Secname ).
Regex Structure	Structure containing flags and regular expression that is used to match the node name.
The example below will only look at Nodes that contain the word suboj.
  Flags = Structure(
                      "Flags",       _Tree,
                       "ObjectRegEx", RegEx( "subobj$" );
                     );

    ForChildren( Child, Starting Point( x ), , "Number Array", Flags )
    {
        Print( child.Name, "\n" );
    };
The output for the example is as follows. Note: The name of the node contains the substring subobj :

frd ex findsec subobj
frd ex findsec subobj
NodeFilter Usage
ForChildren(Child, Starting VT, Filter ) :
In this case Filter is a predicate that combines one or more conditions using logical statements. For example, the following ANDS three conditions. Each condition, specifies the filter value for flag, value type and class ( Security Type).
 Filter = Foldl( Func( a, b ) NodeFilterAnd( a, b ), NodeFilterFlags( _Tree ),
 [ NodeFilterValueType( "Strike" ), NodeFilterClass( Security Type( Sec ) ) ] );
The following shows the contents in Filter:

SDB_CHILD_ENUM_FILTER_SEC_TYPE:SecType=SecDbCompileGraph Filter &&
SDB_CHILD_ENUM_FILTER_VALUE_TYPE:ValueType=Strike &&
SDB_CHILD_ENUM_FILTER_FLAGS:Flags=1
Example
  //Print a list of all currency crosses and their current
  //spot rates

 ForChildren( Child, Dollar Price( "Book: B2" ), "Currency Cross", "Price",  Null )
 {
      Print( Right( Child.Name, 32 ), "  ",
                      Format( Price( Child.Name ), 10, 4, _Commas ),
              "\n" );
 };
See Also
Test: Slang ForChildren All
ForChildrenMultiSet = Func(	src search usage feedback   top
*( Child ),
// Loop variable
Array( InputSet ),
// Array of Secdb Nodes specifying root input nodes
Any( SecTypeFilter ),
// Either a String Security/Interface type or a NodeFilter instance
Any( ValueTypeFilter ),
// For String SecType arg, ValueType name/array of names. Else optional traversal filter
Any( Flags )
// Double or Structure( "Flags", Flags {, "ObjectRegEx", RegEx } )
) Returns( )
Similar to ForChildren with 2 major differences - accepts input set of nodes on which children traversal is performed while minimising re-visiting of the same nodes belonging to subgraphs shared across the input nodes. Reports any failures that occur when building the graph and traversing the children nodes. For the details on other arguments and example of usage see documentation for ForChildren
Alternative traversal mode which is activated with _MultiSet Full Traversal Aggregate flag is available. This traversal mode will traverse full graph across all of the inputs while keeping track of the "ultimate" parent input node for each child. In this mode we will iterate over each unique child only once and Child iterator Structure will have an array of parent inputs populated under "Parents" component

See Also
Test: Slang ForChildren All
ForSecurity = Func(	src search usage feedback   top
*( Variable ),
// Loop Variable
String( Security Type ),
// Security Type
String( StartName ),
// Start Security Name - OPTIONAL
String( EndName ),
// End Security Name - OPTIONAL
Double( ReturnSecurityFlags )
// Indicates whether to return the security, rather than name. Default is False - OPTIONAL.
) Returns( )
Iterates through a list of all securities in the database that belong to a particular Security Type. Any securities in the local session cache (only) are ignored.
If StartName and EndName are specified then the iteration begins with the Security StartName and will stop when Security name equals or exceeds EndName. These arguments provide a range on enumeration and are inclusive.

At each iteration, Variable contains the name of the current Security name, unless ReturnSecurityFlags is specified, in which case the Security pointer is returned (unless it's unloadable, in which case the name is returned). If you wish to pass flags (such as SDB_REFRESH_CACHE), pass the flags, rather than True for ReturnSecurityFlags.

If you wish to get the Error information rather than just a name if the Security is unloadable, you can add the flag SDB_GET_PER_SEC_ERRORS to the ReturnSecurityFlags. This will result in the loop Variable either being a Security pointer or a Structure which contains the Error and ErrNum specific to that iteration's failure, as well as the Security name.

For efficient usage of this function refer see How do I use ForSecurity?.

Example
 //  Print a list of all currency crosses in the database from the range BEF/XEU to ESP/XEU
 ForSecurity( Security Name , "Currency Cross" , "BEF/XEU" , "ESP/XEU")
    Print( Security Name, "\n" );
Output
BEF/XEU
CAD/XEU
CHF/XEU
DEM/XEU
DKK/XEU
ECU/XEU
ESP/XEU 
See Also
NameLookup
ForIndex = Func(	src search usage feedback   top
*( Variable ),
// Loop Variable
Double( StartPos ),
// Starting Index Position
String( Loop Condition ),
// Evaluated at the start and once for each loop iteration just like for
String( Direction )
// One of Get GE/Get LE. Controls the direction of index traversal.
) Returns( )
Iterates through an index from a specified starting position. SecDB indexes are ordered lists. Each index specifies a list of classes it tracks. Some examples of Indexes are: Trades by External Trade Id, Positions by Book, and Trades by Time.
During each iteration, Variable holds information about the current Index. The iteration begins at StartPos and only stops when Loop Condition evalutes to FALSE. The Direction specifies the direction of traversal. The possible values for Direction are:

GET GE:
Traverses the index from Start Pos.
GET LE:
Traverses the index backwards. The starting position is when Loop Condition evaluates to FALSE and the traversal halts at Start Pos. This is very inefficient since it ends up doing one server roundtrip per index record.
The following example iterates through the Index "Trades By External Trade Id".

Example
 IndexName = "Trades By External Trade Id";
 IP        =  NewIndexPos( IndexName );
 LP        =  NewIndexPos( IndexName );

 All Trades = [];

 ForIndex( P, IP, LP; GET GE )
 {
     All Trades &= IndexPosSecurity( P );

 };
See Also
Indexes in SecDB
ForValue = Func(	src search usage feedback   top
*( Value ),
// Loop Variable - Loop variable to hold the current VT name
Any( Sec ),
// String/Security to depict a Security
Double( EnumFlag )
// Flag (True or False) to indicate an Enumerable Structure - Optional
) Returns( )
Iterates through all the VTs for a given security (Sec). Value contains the VT name during each iteration. However, if True is passed for EnumFlag , then Value contains a Structure instead of VT name. The following lists the components of the Structure when this occurs:

Flags	Description
Calculated	True if valuetype is calculated
External	True if valuetype comes from external source
Flags	SDB_VALUE_FLAGS or'ed together
Hidden	True if valuetype is hidden
InStream	True if valuetype is in-stream
Name	Name of valuetype
SetRetained	True if valuetype is retained
Static	True if valuetype doesn't change
Type	Datatype of valuetype
The following example prints all the VT that an object supports.

Example
 Object = "Options";

 ForValue( Val, Object )
   Print( Val, " = ", GetValue( Val, Object ), "\n" );
See Also
For
ForClass = Func(	src search usage feedback   top
*( ClassVar ),
// Iteration variable
Double( DetailFlag )
// TRUE: structure; FALSE: string
) Returns( )
Iterates through all classes in SecDb. During each iteration, ClassVarcontains the name of the current class.
However if DetailFlag is set to True, ClassVar will contain a Structure instead. This Structure is the same as that returned from ClassInfo( Class, False ). This means the information for each Class will be populated differently depending on whether that particular Class happens to already be loaded or not. If the Class is loaded you will get the same Structure as you would get with ClassInfo( Class, True ). If the Class is not already loaded then some fields will not be populated; namely CompressedStream, Implemented Interfaces, loaded, NumInstreams, ObjectCount and ValueTypes.

Note: the data is not retrieved in alphabetical order.

Example
 //Print out a list of classes

  ForClass( ClassName )
      Print( ClassName, "\n" );
See Also
For , ForSecurity
SecDbGraphHash = Func(	src search usage feedback   top
*( Root )
// SecDb Node
) Returns( )
Computes a hash of the shape of the graph below Root, based on VT names & class IDs.
Break = Func(	src search usage feedback   top
) Returns( )
Aborts the flow of the current Loop
Example
 For(i = 0; i < 10 ; i++)
 {
       Print(i , "\n" );
       Break;

 };
Output
The output: 0
The Loop terminates in the first iteration
See Also
Continue, While, For
Continue = Func(	src search usage feedback   top
) Returns( )
Skips to the next iteration in a loop. In the example below, hello is not printed. Instead, by calling Continue, the program jumps to the next iteration.
Example
 For( i = 0 ; i < 6 ; i++ )

     {  print(i , "\n");

       continue;
       print("hello\n")

     };
Output
0
1
2
3
4
5
See Also
Break, For, While
Exit = Func(	src search usage feedback   top
Double( ReturnValue )
// Return Value
) Returns( SLANG_RET_CODE )
Stops the current Slang evaluation and returns ReturnValue.
This function is typically used to force SecExpr to return ReturnValue to the operating system (when it's invoked with the '-l' flag). ReturnValue can then be passed to a command shell script.

Example
 //   Stop entire script when error detected.
 Set = Func( SecPtr, ValueName, Value )
 {
   if( !SetValue( ValueName, SecPtr, Value ))
      Exit( 99 );
 };
See Also
AtExit, Abort, Return, TransactionAbort.
Abort = Func(	src search usage feedback   top
) Returns( )
Simulates a press of the Abort key.
This function is used to simulate a press of the Abort key. If using AbortTrap, Abort can be placed either inside the AbortTrap block (to simulate the user aborting), or outside the AbortTrap (to continue with the abort processing). Note, though, that AbortTrap has been deprecated.

See Also
AbortTrap, AbortCheck, Error
AbortTrap = Func(	src search usage feedback   top
) Returns( Double )
DEPRECATED
For = Func(	src search usage feedback   top
*( InitExpression ),
// Initialization Expression
*( CondExpression ),
// Conditional Expression
*( IncExpression )
// Increment Expression
) Returns( )
Executes a looped conditional expression.
Slang evaluates InitExpression. This initializes the loop variable.
While the conditional expression CondExpression evaluates to a True value, the block of code is executed and the loop expression IncExpression is evaluated.
When CondExpression turns to False, control passes to the statement following the For loop.
You can affect iteration by calling the following functions from within the loop:

Break, which will force a premature exit from the loop.
Continue, which will jump to the next iteration of the loop, bypassing any other instructions within the block.
Example
 // Print out all even numbers from 0 to 10
 For( Number = 0; Number <= 10; Number += 2 )
 {
     Print( Number, "\n" );
 };
Output
 0
2
4
6
8
10 
See Also
While, Break, Continue, ForEach, ForComponent
Switch = Func(	src search usage feedback   top
( MatchExpression ),
// Match Expression
Ellipsis( CaseExpression ),
// Case Expression
Ellipsis( EvalExpression ),
// Eval Expression
( DefaultEvalExpression )
// Default Expression
) Returns( Double )
Executes a matched conditional expression.
This function evaluates MatchExpression, attempting to match results with each CaseExpression. If a match is found, it executes the associated EvalExpression. If no match is found, and a DefaultEvalExpresion exists, it executes that (default) expression.

The function returns the result of the evaluated EvalExpression.

Usage
Switch( MatchExpression, CaseExpression 1, EvalExpression 1, CaseExpression 2, EvalExpression 2, . . . CaseExpression N, EvalExpression N, [ DefaultEvalExpression ] )
Example
 //   The first Switch function converts a numeric value
 //   to a string.  The second displays different things
 //   based upon the type of data
 Numeric Value = 2;
 String Value = Switch( Numeric Value,
 1,   "One",
 2,   "Two",
 3,   "Three" );

 Print( Switch( TypeOf( Value ),
                "Double", Format( Value, 20, 4, _Commas ),
                "String", Left( 20, Value ),
                "Curve",  "Curve",
                "Array",  "Array",
                "Date",   Value,
                "Time",   Value,
                Value )); // Last is default
See Also
If
AbortCheck = Func(	src search usage feedback   top
Double( CheckFrequency )
// Minimun # of seconds between checks
) Returns( )
Specifies how frequently SecDb polls for an abort action (e.g., the Escape key).
The CheckFrequency argument is the number of seconds between checks. You can also specify one of the following:

0 - always check.
< than 0 - never check.
Usage
Common reasons for calling this function include:
Speeding up some part of a script at the expense of possibly delaying an interrupt from the user
Delaying an abort action until some uninterruptable piece of code has finished execution (note that the abort is only delayed, not ignored).
Example
  AbortCheck( -1 )
  {
       // Some uninteruptable code here
  };
  // The abort action will be held until this point
See Also
AbortTrap, Abort
Lambda = Func(	src search usage feedback   top
Ellipses( Arguments )
// Any Number of Arguments
) Returns( Slang )
Lambda is essentially an expression that returns a function. In order to allow users to operate on the data in an application, we need a mechanism for defining functions that have knowledge of the environment in which they're called. In Slang, this mechanism is called a Lambda.
The example below constructs a lambda when called returns a function. The variable I within the function, becomes the the Global variable for the function. Any data modification to the variable is cached within the scope. The next time, the variable is accessed, the value read is the modified value

Example
 New Counter = Func()
 {
     I = 0; // Global Scope within the Function
     Return( Lambda()
             {
                 Return( I++ ); // Increment I
             }
           );
 };

 Print( "Testing counter.\n" );
 Counter = @New Counter;
 Print( @Counter , "\n" ); // Since Counter is a function, Use @ to call the function
 Print( @Counter , "\n" );
 Print( @Counter , "\n" );
Output
Testing counter.
0
1
2 
Closure = Func(	src search usage feedback   top
Ellipses( Arguments )
// Any Number od Arguments
) Returns( Slang )
DEPRECATED - Use Lambda
Error Handling Top
Error = Func(	src search usage feedback   top
) Returns( Error )
A constructor for the Error datatype (and takes no arguments). and returns a datatype. The example defines anError as an Error datatype. isError is used to check if the arugment passed is of type Error. It returns true if the conditional passes. Note isError(null) always evaluates to true.
Example
 anError = Error();
 isError(anError); // returns true
See Also
Error handling in Slang
RedboxSuppress = Func(	src search usage feedback   top
Double( State )
// New State
) Returns( )
Evaluates the enclosed block, suppressing redboxes. If you specify a State then it will be the new value of SecviewSuppressRedboxes at the end of the block.
Usage
RedboxSuppress( NewStateAtEndOfBlock ) { BLOCK; };
The tolerance of the SecDb graph evaluator to invalidation errors can be also controlled by

By evaluating RedBoxSuppress(level), which sets the tolerance level until the next RedBoxSuppress call, or until exiting an enclosing RedBoxSuppress block. The ForceSuppress argument overrides the previous level. For backward compatibility, the tolerance levels are 1, 0, and -1.
Level 1 means no severe graph errors are reported.
Level 0 means severe graph error will be reported with the addins returning False or Null but no error popups.
Level -1 means severe graph errors will be reported along with error popups. When Esc is pressed, the flow gets into the debugger. One can continue from there and the behavior is same as that of level 0 until another severe graph error is encountered. This level is highly useful and suggested for fixing severe graph errors.
It is strongly recommended that newly developed code is tested and runs without errors at level -1 (with the above configuration settings).

See Also
Why do I get node invalidation errors?
ForFile = Func(	src search usage feedback   top
File( File ),
// Loop variable that holds the file name
String( FileSpec ),
// File Specification. This holds the directory path and pattern of file to search for.
Double( Detail )
// Boolean
) Returns( )
Iterates through all files specified in FileSpec in the current directory. During each iteration, File holds reference to the current file name. If FileSpec is not specified, then the iteration starts at the current directory. The FileSpec can contain both a path and a file pattern. ForFile( file, u:/bar/foo/<wildcard>.csv) searches for all csv files under the directory u:/bar/foo.
File usually contains the file name at each iteration however when you set Detail flag to True, File will now be a Structure that contains the following components:


Name	Description
Executable	Is file executable
File Type	Type of file, e.g., "Regular File"
Name	Name of the file (without directory)
Readable	Is file readable by current user
Size	Size of the file
Time Accessed	Time file was last accessed
Time Created	Time file was created
Time Written	Time file was last written
Writable	Is file writable by current user
Usage
ForFile( Variable ,FileSpec ,Detail ) { BLOCK; };
Example
 //   Print a list of all files with a '.rpt' extension,
 //   and the times the files were created
 ForFile( File, "*.rpt", True )
 Print( File.Name, " ", File.Time Created, "\n" );
See Also
For
Function Definition Top
Return = Func(	src search usage feedback   top
Ellipses( Expression )
// Expression
) Returns( )
Terminates execution of the function in which it appears and returns control (and the value of Expression if given) to the calling function. If a function is defined to return a specific dataype, then the datatype of the Expression should evaluate to the specified datatype. The example below returns an array with elements 1,2,3,4
Example
Return ( [1,2,3,4] );
Returns = Func(	src search usage feedback   top
Ellipses( Datatype )
// Datatype
) Returns( )
Function signature indicating one or more datatype that the function returns If the Function does not return a value, then the parameter can be left empty or this keyword does need not to be used.
Example
 FuncReturnArray = Func()
 Returns( Array() )
 {
   Return ( [1,2,3,4,5] );
 };
Value Specs:
Return parameters can also take an optional Value Spec which will validate post conditions on the return value.
Example
 MyValueSpec = Func()
 Returns( String( Spec::String( Min Size := 1 ) ) )
 {
   Return( "" );
 };
 @MyValueSpec
Output:
Type mismatch, failed spec check on return
Value "" has 1 validation error: has size 0 < min length of 1
Special Cases:
Note also the following special cases in Returns (examples below):
You can return a StructureCase() from a function which specifies a Structure() return
GsDt types will automatically be converted if possible
Examples
 MyStructureFunc = Func()
 Returns( Structure() )
 {
   Return( {\ Case Sensitive := True \} );
 };
 [ R = @MyStructureFunc; TypeOf( R ) ];
Output:
[ Case Sensitive: 1, StructureCase ]
 MyGsDtFunc = Func()
 Returns( GsDt() )
 {
   Return( "I'm a DtString" );
 };
 [ R = @MyGsDtFunc; DataTypeOf( R ) ];
Output:
[ I'm a DtString, GsDtString ]
 MyStringFunc = Func()
 Returns( String() )
 {
   Return( GsDtString( "I'm a GsDtString" ) );
 };
 [ R = @MyStringFunc; DataTypeOf( R ) ];
Output:
[ I'm a GsDtString, String ]
 MyDictionaryAsStructFunc = Func()
 Returns( Structure() )
 {
   Return( GsDtDictionary( [ "Key", "Value" ] ) );
 };
 [ R = @MyDictionaryAsStructFunc; DataTypeOf( R ) ];
Output:
[ Key: Value, Structure ]
 MyStructAsDictionaryFunc = Func()
 Returns( GsDt() )
 {
   Return( {| Key := "Value" |} );
 };
 [ R = @MyStructAsDictionaryFunc; DataTypeOf( R ) ];
Output:
[ Key: Value, GsDtDictionary ]
Finally = Func(	src search usage feedback   top
) Returns( )
A Finally block at the end of a Func block is executed either when the function returns or when an uncaught exception propagates out of the function. This is helpful for clean up code that should run no matter whether the function succeeds or fails.
Modern practice is that resources should clean themselves up rather than rely on external code to do it for them. See How do I use exceptions in Slang?.

The following example displays a function that uses Finally to destroy and delete the File reference created while openingi a File.

Example
 G = Func() { Throw( 2 ); };

 F = Func() Returns()
    {
        Temp Name = FileTempName();
        File = FileOpen( Temp Name, FILE_OPEN_WRITE );
        Print( "Calling G\n" );
        @G();
    }
    : Finally()
    {
       Destroy( File );
       FileDelete( Temp Name );
       Print( "Finally cleaning up F. ", Temp Name, " was deleted\n\n" );
    };

  // Call Function
  Try( X )
  {
      @F();
  }
  :
  {
      Print( "Got an exception: ", X, "\n" );
  };
A Finally block can only be bound to a Returns statement (beneath a Func or Lambda).

Throw = Func(	src search usage feedback   top
Any( Object ),
// Object to Throw/Exception to Rethrow
Double( ErrorCode ),
// Error constant, defualt _ERR_UNKNOWN - Optional
Slang Node( Node )
// Node where the error actually happened - Optional
) Returns( )
An exception is an occurrence that causes a program to stop executing its normal sequence of commands and, instead, to execute a chunk of code specifically designed to handle the occurrence. Slang implements exceptions using the Try and Throw primitives.
The Throw primitive sits within a function and takes Object (it can also take an optional ErrorCode). If an exception occurs during execution of the function, the function "throws" the object to the code that called it. The thrown object can be of any type, and is the analog of a Return'ed value: think of Throw as a super-Return, which passes not to the code that called the function, but to the first Try block.

All methods use the throw statement to throw an exception. Functions at times need to throw execption in case of errors/exceptions that were generated during executions. In the example below, G throws an Expection. The value 2 (the data that was returned as a result of the Throw statement) can be retrieved by accessing the Object attribute of X. X is of datatype Execption.

Example
 G = Func() { Throw( 2 ); };

 F = Func() Returns()
    {
        @G();
    }
    : Finally()
    {
       Print( "Finally cleaning up F. " was deleted\n\\n" );
    };

  // Call Function
  Try( X )
  {
      @F();
  }
  :
  {
      Print( "Got an exception: ", X, "\n" );
  };
Output
 Finally cleaning up F.   was deleted
\nGot an exception: ErrorCode: Unknown
SlangModuleName: Untitled-2
SlangLineNum: 1
SlangLineEndNum: 1
SlangColNum: 15
SlangColEndNum: 25
CPPModuleName:
CPPLineNum: 0
LastError: SlangParser: Script has an error at (or near) 'Symbol':was deleted
SlangParser: Line#    8 Column#   73
SlangParser: Gramatical error,
parse error, expecting `SL_SEMICOLON' or `SL_RPAREN' or `SL_COMMA' or `SL_EOF_TOKEN'
Object: 2 
See Also
How do I use exceptions in Slang? , Example: Slang Errors
Mush Top
GobMushInStreamValues = Func(	src search usage feedback   top
Security( SecPtr ),
// Security Pointer
Array( ChildData ),
// Instream values
Double( DoNotIgnore )
// Include GOB_MUSH_IGNORE values
) Returns( Double )
Returns a 32-bit hash value of SecPtr's instream values passed in ChildData (typically provided by In Stream Children( Self ) ).
NB. GobMushInStreamValues has a number of limitations (e.g. incorporates the name rather than content of instream securities) and is not recommended for use in Implied Name construction of new Security types.

See How does Implied Name work? for more details on Implied Name.

GobMushString = Func(	src search usage feedback   top
Double( Number ),
// Mush Value
Double( Width )
// Buffer Size
) Returns( String )
Create a string using secdb name friendly characters from a mush value.
GobMushStringToDouble = Func(	src search usage feedback   top
String( String )
// String Value
) Returns( String )
Create a mush string from a string.
Encryption Top
System Top
HeapInfo = Func(	src search usage feedback   top
) Returns( Structure )
Returns a Structure containing information about allocated memory. Components in returned structure are as follows:

Component	Description
Free	Amount of memory available
Nodes	Number of pieces of memory allocated
Nodes (Free	
Unused	Amount of memory allocated and currently unused
Used	Amount of memory currently in use
Example
 foo = HeapInfo();
 Print(foo);
Output
Free        : 1515626496
Nodes       : 1023495
Nodes (Free): 0
Unused      : 0
Used        : 53801136
See Also
HeapUsed
ProcessFork = Func(	src search usage feedback   top
Double( ReallyFork )
// Pass TRUE to fork
) Returns( )
Standard Unix fork
ProcessWait = Func(	src search usage feedback   top
Double( PID ),
// Process ID to wait for - Optional
Double( NoHang )
// Don't block; just check if process is active - Optional
) Returns( )
Waits for the Process attached to Process ID to terminate before continuing with the next execution step. Standard waitpid on POSIX and WaitForSingleObject on Win32.
ProcessKill = Func(	src search usage feedback   top
Double( PID )
// Process ID
) Returns( )
Kills the process that is associated with PID
Example
 //Kill self. Note when you execute this your secview session will terminate.
 ProcessKill( ProcessID() ); //
ProcessCpuTime = Func(	src search usage feedback   top
Double( Block )
// Boolean to indicate
) Returns( Double )
Retrives the actual CPU time used by slang session A Double is returned depicting the CPU usage in seconds for the current slang process (CPU time during system calls in NOT included).
Example
 If( ( CpuTime = ProcessCpuTime() ) == Null )
 {
    Print( LastError() );
 }:
 {
    Print( "CPU usage so far = ", CpuTime, "\n" );
 };
ProcessAffinityMaskSet = Func(	src search usage feedback   top
Double( AffinityMask ),
// Subset of mask returned by ProcessAffinityMask
Double( ProcessId )
// Defaults to current process - Optional
) Returns( Double )
Sets affinity mask for this process .
ProcessDirectoryGet = Func(	src search usage feedback   top
String( Name ),
// Name of process directory block
Size( Double )
// Maximum number of bytes to return
) Returns( )
Fetches contents of Win32 shared memory block with given name
ProcessDirectoryPut = Func(	src search usage feedback   top
String( Name ),
// Name of process directory block
Data( Binary )
// Data to copy into the block
) Returns( )
Copies data into Win32 shared memory block with given name
ProcessDirectoryLock = Func(	src search usage feedback   top
String( Name ),
// Name of process directory block
Timeout( Double )
// Timeout (milliseconds)
) Returns( )
Acquires exclusive lock on named Win32 shared memory segment.
ProcessDirectoryUnlock = Func(	src search usage feedback   top
String( Name )
// Name of process directory block
) Returns( Boolean success; Null on non-Win32 )
Releases exclusive lock on named Win32 shared memory segment.
Link Top
SmartLink = Func(	src search usage feedback   top
String( ScriptName ),
// Name of script to SmartLink
Double( ForceRelink )
// TRUE to force script to be linked - Optional
) Returns( )
Parses SmartLinkEnabled libraries at run-time.
See Also
When do I need to use SmartLink?
Include = Func(	src search usage feedback   top
String( ScriptName )
// Name of script to SmartLink
) Returns( )
Includes and evaluates the contents of another script. This function is used to link in functions and constants from other scripts. Since Slang is an interpreted language, the script that is included will be immediately parsed and evaluated. This function is evaluated at run time while the Link function happens at parse time. Link is the prefered function.
See Also
Link, Func, Function, Eval
EvaluateSuperLinkedScript = Func(	src search usage feedback   top
String( ScriptName )
// Name of script to SmartLink
) Returns( )
Includes and evaluates the given named script much like Include, but specifically for use by Slang SuperLink where the script to be evaluated is already cached in SuperLink.
Used by Slang SuperLink - not intended for any other direct use.

CurrentModuleName = Func(	src search usage feedback   top
) Returns( String )
Returns the name of the Current Script.
Indexes Top
NewIndexPos = Func(	src search usage feedback   top
String( IndexName )
// Index Name
) Returns( Index Pos Index )
NewIndexPos is used to create a new Index Pos Index datatype. An Index Pos Index is a cursor into an index in the database. The function returns Null if IndexName not valid
Typically, New Index Pos datatype is used with ForIndex to iterate through an index. Index Pos Index datatypes functions in many ways like structures. You can reference field data within an Index Pos by using the '.' operator. Components within an Index Pos can be accessed and assigned to in the same way as structures.

Example
 IndexName = "Trades By External Trade Id";
 IP        = NewIndexPos( IndexName );
See Also
IndexGet , Indexes in SecDB
IndexPosSecurity = Func(	src search usage feedback   top
Index Pos Index( Index )
// Index Pos Index
) Returns( Any )
Retriveves the item/data stored from a Index Pos Index datatype. In the example below calling IndexPosSecurity on Index gets the data stored in the Index. In this case only Trade ids are stored as strings.
Example
 IndexName = "Trades By External Trade Id";
 IP        = NewIndexPos( IndexName );
 ForIndex( Index, IP, IP , Get GE )
 {
    Foo = IndexPosSecurity(Index); //  eg Foo = Trade  862128898
 };
See Also
IndexGet
IndexGetByName = Func(	src search usage feedback   top
String( IndexName ),
// Name of index to use
Double( GetType ),
// Type of index operation
String( SecName )
// Security Name
) Returns( Any )
Retriveves the item/data stored in a Index. The data is fetched based on:
IndexName - This is the Name of the Index. In the example below the name is "Books By Group";
SecName - The name of the security that is stored in the index
GetType : The following are the various types of index operation. Each type compares againts SecName
Index Operator	Description
_Equal	lookup Equal
_First	lookup First
_Ge	lookup Greater than or equal to
_Greater	lookup Greater
_Last	lookup Last
_Le	lookup Less than or equal to
_Less	lookup Less
_Next	lookup Next
_Prev	lookup Prev
Example
 IndexName = "Books By Group";
 BookName = "00122274 cus";
 IndexByName = IndexGetByName( IndexName, _Equal, BookName );
 Print(IndexByName);
Output
Index: Books by Group
SecName: 00122274 cus

Group:
Book Type:
See Also
IndexGet
IndexGet = Func(	src search usage feedback   top
IndexPos( IndexPos ),
// Index position
Double( GetType )
// Type of index operation
) Returns( Any )
Retrieve data from an index
Returns
Name of object matching get operation
The IndexPos is a cursor into the database that was created with the NewIndexPos function. The following methods can be used for placing the cursor:

GetType Constants	Description
_Equal	lookup Equal
_First	lookup First
_Ge	lookup Greater than or equal to
_Greater	lookup Greater
_Last	lookup Last
_Le	lookup Less than or equal to
_Less	lookup Less
_Next	lookup Next
_Prev	lookup Prev
See Also
NewIndexPos, IndexInfo, IndexNames
Example
 //Print positions expiring in the next year
 Start Date   = Current Date( "Security Database" );
 End Date = Start Date + 365;

 Index = "Positions by Expiration Date";

 Index Pos = NewIndexPos( Index );
 Index Pos.Expiration Date = Start Date;

 Limit Pos = NewIndexPos( Index );
 Limit Pos.Expiration Date = End Date;

 For( Pos Name = IndexGet( Index Pos, _Ge );
 Pos Name && Index Pos <= Limit Pos;
 Pos Name = IndexGet( Index Pos, _Next ))
 {
    Print(    Left( 32, Pos Name ),               " ",
    Left( 32, Index Pos.Book Name ),  " ",
    Index Pos.Expiration Date,            " ",
     Index Pos.Quantity,                  "\n" );
  };
IndexNames = Func(	src search usage feedback   top
) Returns( Array )
Returns an array of index names. The IndexInfo function can be used to display the structure of an individual index.
Example
 //   Print detail on each index
 Indices = IndexNames();
 ForEach( Index, Indices )
 Print( IndexInfo( Index ), "\n" );
See Also
IndexInfo, IndexGet
IndexInfo = Func(	src search usage feedback   top
String( IndexName )
// Index Name
) Returns( Structure )
Returns information about an Index. The returned structure contains the following:

Components	Description
Classes	Array of classes (security types) that the index applies to.
Name	Name of the index.
Parts	Array of part structures (detailed below.)
The Parts structures have the following components:


Components	Description
ByteWidth	Width of the field.
Flags	Numeric/Non-numeric, Ascending/Descending.
ValueType	Value type.
Example
 //Print the format of the 'Trades by Time' index
 Print( IndexInfo( "Trades by Time" ));
Output
Classes       :
[   0] = Trade
Flags         : 0
Name          : Trades by Time
parts         :
[   0] = ByteWidth: 32
Flags    : 9
ValueType: Group

[   1] = ByteWidth: 32
Flags    : 9
ValueType: Location

[   2] = ByteWidth: 8
Flags    : 5
ValueType: Trade Time

TotalByteWidth: 48
See Also
NewIndexPos, IndexGet, IndexNames
IndexRepair = Func(	src search usage feedback   top
String( SecName ),
// Security to be fixed
Double( Force ),
// Removes the Security from all indices, including those it's not supposed to be in (Default: FALSE)
String( IndexName )
// If provided, Only this Index is repaired.(Default: "")
) Returns( Any )
When IndexName is not provided: Repairs SecName in secdb database indexes, by removing it from the indexes it belongs to, and reinserting. The Force arg causes it to be removed from all indexes, including those it's not supposed to be in, and then reinserted in the correct indexes.
When IndexName is provided: Repairs SecName only in the given Index, by removing and reinserting. The Force arg causes it to be removed from the Index even if SecName is not supposed to be in that Index Note: IndexName must be a non IDS Index. Note: Please use this with caution.

To better illustrate the function, consider the following scenario:

Sec1 lives in Index1 - Incorrect Index
Sec1 lives in Index2 - Correct Index
Sec1 lives in Index3 - Correct Index
Sec1 lives in Index4 - Incorrect Index
Sec1 does not live in newly created Index5 but should

Calling IndexRepair( Sec1, Force := False )
Sec1 lives in Index1 - Incorrect Index
Sec1 lives in Index2 - Correct Index - re-inserted
Sec1 lives in Index3 - Correct Index - re-inserted
Sec1 lives in Index4 - Incorrect Index
Sec1 lives in newly created Index5 - Correct Index

Calling IndexRepair( Sec1, Force := True )

Sec1 lives in Index2 - Correct Index
Sec1 lives in Index3 - Correct Index
Sec1 lives in newly created Index5 - Correct Index

Calling IndexRepair( Sec1, Force := False, IndexName := "Index2" )

Sec1 lives in Index1 - Incorrect Index
Sec1 lives in Index2 - Correct Index - re-inserted
Sec1 lives in Index3 - Correct Index
Sec1 lives in Index4 - Incorrect Index
Sec1 does not live in newly created Index5 but should

Calling IndexRepair( Sec1, Force := True, IndexName := "Index1" )
Sec1 lives in Index2 - Correct Index
Sec1 lives in Index3 - Correct Index
Sec1 lives in Index4 - Incorrect Index
Sec1 does not live in newly created Index5 but should

Calling IndexRepair( Sec1, Force := False, IndexName := "Index1" )
Sec1 lives in Index1 - Incorrect Index
Sec1 lives in Index2 - Correct Index
Sec1 lives in Index3 - Correct Index
Sec1 lives in Index4 - Incorrect Index
Sec1 does not live in newly created Index5 but should
Example
 SecName = "SUSP-LDN";
 If( !IndexRepair( SecName ) )
   {
       Print( "*** Failed: ", LastError(), "\n" );

   }
Buffer Top
OutputBufferNew = Func(	src search usage feedback   top
String( Title )
// Title of output buffer
) Returns( )
Clear the output buffer and set a new title if supplied
OutputBufferBrowse = Func(	src search usage feedback   top
) Returns( )
Allow user to browse though the output buffer. When the user hits Escape, the script continues evaluation.
OutputBufferSave = Func(	src search usage feedback   top
) Returns( )
Save the contents of the current output buffer. The Title of the output buffer (set with OutputBufferNew) is also saved with the report.
OutputBufferSetFore = Func(	src search usage feedback   top
Double( Color )
// Foreground Color (GxRGB)
) Returns( )
OutputBufferSetBack = Func(	src search usage feedback   top
Double( Color )
// Background Color (GxRGB)
) Returns( )
Sets the foreground for the output buffer
Pack Top
BinaryFromInt32 = Func(	src search usage feedback   top
Binary( Data )
// Four bytes of binary data
) Returns( )
Convert binary from Int 32.
Example
 x = BinaryFromInt32( 5 ); // x= 2
BinaryToInt32 = Func(	src search usage feedback   top
Binary( Data ),
// Four bytes of binary data
Double( Signed )
// True(default)/False - Optional
) Returns( )
Convert binary to Int 32.
Example
 x = BinaryFromInt32( 5 ); // x= 2
 BinaryFromInt32( x) ; // returns 5
Output Top
PageAt = Func(	src search usage feedback   top
Page( Page ),
// Page containing the formatted Expression
Double( x ),
// starting x index for each line of Text
Double( y ),
// starting y index for each line of Text
Ellipsis( Expression )
// Expression that will be formatted and stored in Page.
) Returns( )
This function puts text into a Page datatype. A Page datatype is a buffer (containing rows and columns) for holding text. The x, y arguments indicate the starting location within the Page. The x denotes the row and y denotes the column. Each expression is evaluated, converted into a string and written to the Page. To view the Page, the user must use Print. The function also wraps carriage returns in an intelligent manner.
EXAMPLE
 PageAt(Page, 1 , 1, "Hello" , " World" );
 Print(Page);
OUTPUT
_________________________________
|                               |
| Hello World                   |
|_______________________________|
SEE ALSO
PageBox , Page , StrWidth , StrHeight , Sheet
PageBox = Func(	src search usage feedback   top
Page( Page ),
// Page that will eventually contain the formatted Expression
Double( XLow ),
// X Min
Double( Ylow ),
// X Low
Double( XHigh ),
// X Max
Double( YHigh ),
// Y Max
Double( Width )
// Width
) Returns( )
Draws lines on the boundry of the Page datatype which is defined by the coordinates specified in the parameters. The Xlow, Ylow and Xhigh, Yhigh arguments contain the four corners of the box. If Xlow and Xhigh are the same, a vertical line is drawn. If Ylow and Yhigh are the same, a horizontal line is drawn.
Example
Prints list of numbers formatted
 MaxColumns    = 4;
 MaxRows   = 10;
 ColWidth  = 10;
 Row = Column  =  0;
 Page = Page();
 Foo = [1,2,3,4,5,6,8,9,10];

 PageBox( Page, 0, 0, MaxColumns * ColWidth + 2, MaxRows + 2 );
    ForEach( element, Foo )
    {
       PageAt( Page, 1 + Column * ColWidth, 1+Row, element );
       If( Row++ >= MaxRows )
       {
         Row = 0;
         If( ++Column >= MaxColumns )
         {
           Print( Page );
           Row = Column = 0;
           Page = Page();
           PageBox( Page, 0, 0, MaxColumns * ColWidth + 2, MaxRows + 2 );
          };
      };
    };

   Print( Page );
Output
pagebox.jpg
SEE ALSO
PageAt , Page , Sheet
Printf = Func(	src search usage feedback   top
String( FormatString ),
// Format String
Eliipses( Expression )
// One or more Expression
) Returns( )
Writes FormatString to the current print handler replacing format specifiers with the additional arguments.
The default print handler for secexpr will write to stdout and for secview output is written to the Evaluation Output window. Output can be redirected using PrintToFile, PrintToObject and their Tee forms.

Usage
See Sprintf for FormatString details.
See Also
Sprintf, FillIn, Right, Left, Center, Format, PrintToFile, PrintToObject, TeePrintToObject, TeePrintToFile
Sprintf = Func(	src search usage feedback   top
String( FormatString ),
// Format String
Ellipsis( Expression )
// One or more Expressions
) Returns( String )
Like C's sprintf function, this function takes a format string and replaces its format specifiers with the formatted form of the additional arguments.
Usage
Sprintf supports most of the standard C format specifiers and some extensions for %s. %s is typically used for String arguments but maybe used for any datatype that supports conversion to String. The number of arguments following FormatString should match the number of format specifiers.
Format specifiers have the following form, %[flags][width][.precision]specifier.

Specifiers
Specifiers are typically the ones that represent the datatype of the expression passed in the additional arguments. For example, if a user wants to format a Double, then d can be used as a specifier.

Specifier	Description	Example
d	Integer representation	392
i	Same as d	392
s	String	Hello World
e	Scientific notation with e for exponent separator	3.9265e+2
E	Scientific notation with E for exponent separator	3.9265E+2
f	Decimal floating point	392.651111
g	Shortest form of %f or %e	392.65
G	Shortest form of %f or %E	392.65
v	Provide something meaningful in the provided space.	
 Sprintf( "%20v", Curve )
Gives a twenty character or less description of the curve.
m	Mush compatible string (if different than String cast).
This is provided for portable and backward-compatible
hash codes in SecDb tradable security names.	
Flags
Format flags are included with the modifiers to format the arguments.

Flags	Description
-	Left justify by the width specified. By default the expression is right justified
+	Forces the expression to include a + sign
%n(s,d,etc..)	Left-pads the value with ' ' to achieve the required width
 Sprintf( "|%8s|", "hello"); // |   hello| where hello is preceded by 3 spaces
0	Left-pads the number with '0' to achieve the required width
,	Adds a comma separator between each 1000 unit
@	Displays the scaled value of the number (m or k)
 Sprintf( "%@s", 3100000 ) // 3.1m
&	The value is formatted as value * 100 concatenated with a % sign
^	Value is formatted to the center
?	Value is right justified
#	Displays upto 12 Decimal places.
If the number of number of digits is less then 12, then the value is padded with 0s
>	Right justified
<	Trim Leading zeros and space
_	Replaces the zero with blanks
)	Adds a bracket after the number
Width
The Width attribute specifies the width of the formatted expression. For example, using %010d for 3.4 will result in 0000003.4 where the total character length will equal the width (10 in this case).

Width	Description
number	Minimum number of characters to be printed.
If the value to be printed is shorter than this number,
the result is padded with blank spaces.
If the width is less then the length of the value, then it
will remain the same and not be truncated.
Precision
Specifies the minimum number of digits to be written. The result is varied depending on the specifier. The following displays the various precisions with the respective specifier.

Specifier	Description and Example
%s	For example %.2s on the expression "ABCD" will result in "AB"
%d	For example %.4d on the expression 12345.787878 will result in 12345
%i	For example %.4i on the expression 12345.787878 will result in 12345
%f	For example %.4f on the expression 45678.112233 will result in 45678.1122
%e	For example %.4e on the expression 45678.112233 will result in 4.5678e+004
%E	For example %.4E on the expression 45678.112233 will result in 4.5678E+004
%g	For example %.4g on the expression 45678.112233 will result in 4.5678e+004
%G	For example %.4G on the expression 45678.112233 will result in 4.5678E+004
Examples
 Printf( "Decimals: %d \n", 1977 );
 Printf( "Preceding with blanks: %10d \n", 1977 );
 Printf( "Preceding with zeros: %010d \n", 1977 );
 Printf( "floats: %4.2f %+.0e %E \n", 3.1416, 3.1416, 3.1416 );
 Printf( "Width trick: %*d \n", 5, 10 );
 Printf( "%s \n", "A string" );
 n = _Pi * -1000;
 [
     s1 = Sprintf( "%,10.3s", n ), // Format with commas
     s2 = Sprintf( "%<10.2s", n ), // Left justify
     s3 = Sprintf( "%10.2e",  n ), // Scientific format
     s4 = Sprintf( "String: '%s'\nNumber: %d\n", "Test String", 1234 ), // Mixed string & number
 ]
Decimals: 1977
Preceding with blanks:       1977
Preceding with zeros: 0000001977
floats: 3.14 +3e+000 3.141600E+000
Width trick:    10
A string
[   0] = -3,141.593
[   1] = -3141.59
[   2] = -3.14e+003
[   3] = String: 'Test String'
Number: 1234
See Also
Printf, FillIn, Right,Left, Center, Format
Cache Top
CachedSecurities = Func(	src search usage feedback   top
String( SecType )
// Null for any - Optional
) Returns( Structure )
Retrieve a list of cached securities (including those with reference counts of 0). This function returns a structure in which security names are tags and reference counts are values.
SecDbLiteralLruCache = Func(	src search usage feedback   top
) Returns( Array )
Returns a list of literal nodes in the LRU cache as a SecDb Node.
SecDbLiteralLruCacheFlush = Func(	src search usage feedback   top
) Returns( )
Removes all literal nodes from the LRU cache.
Databases Top
InfiniteTransLogDb = Func(	src search usage feedback   top
Database( Db )
// Database requiring infinite trx log - Optional
) Returns( Database )
Returns the infinite transaction log database for the provided Database
 InfiniteTransLogDb( [Db] );
The log file is specified via configuration variables called SECDB_INFINITE_TRX_LOG.* in dbaliases.dat

SourceDatabaseSet = Func(	src search usage feedback   top
Any( NewSourceDbName )
// Set source db to this (Db or name) - Optional
) Returns( Database )
Sets the sourcedatabase to NewSourceDb(Name), and returns the new Source Database of the SecView session.
Securities Top
GetUniqueID = Func(	src search usage feedback   top
) Returns( Double )
Returns a unique number. The number is guaranteed unique for a database.
Usage
GetUniqueID()
See Also
SecDbUniqueID
ClassInfo = Func(	src search usage feedback   top
String( ClassName ),
// Name of class
Double( Pass False to prevent class being loaded )
// Load Class
) Returns( Structure )
Get the class information for the named class.
Example
  DeclareClass( 10606, "Elec Physical", "Elec UFO Physical" );
  Info Unloaded = ClassInfo( "Elec Physical", False );
ClassInfoByID = Func(	src search usage feedback   top
Double( ClassID ),
// Class ID
Double( Pass False to prevent class being loaded )
// Load Class
) Returns( Structure )
Get the class information for the named class.
Example
  DeclareClass( 10606, "Elec Physical", "Elec UFO Physical" );
  Info Unloaded = ClassInfoByID( 10606, False );
ClearLoadHistory = Func(	src search usage feedback   top
) Returns( )
Clears the TrackLoad log.
FAQ entry available.

TrackLoadHistory = Func(	src search usage feedback   top
) Returns( Previous value of On_or_Off )
Enables the TrackLoad code to log successful SecDB object gets in a list accessible via GetLoadHistory.
FAQ entry available.

TrackLoadHook = Func(	src search usage feedback   top
) Returns( Previous value of On_or_Off )
Enables the TrackLoad code to send a log of successful SecDB object gets to a callback registered with SetLoadHook.
FAQ entry available.

TrackLoadCallDepth = Func(	src search usage feedback   top
) Returns( Previous value of Depth )
Sets the height of the call stack saved by TrackLoad. Defaults to 1.
FAQ entry available.

SetTrackLoadHook = Func(	src search usage feedback   top
Slang( Hook )
// Hook to call. Of the form: Func( String )
) Returns( )
Sets callback to call for successful object gets in TrackLoad. The callback receives one parameter, a Structure describing the call.
FAQ entry available.

GetLoadHistory = Func(	src search usage feedback   top
) Returns( Array of Structures. )
Returns TrackLoad log about object gets. Enabled through TrackLoadHistory.
FAQ entry available.

ConfigurationGet = Func(	src search usage feedback   top
String( Name ),
// Configuration variable to get (Null for entire config) - Optional
String( File ),
// Config file (default secdb.dat) - Optional
String( Path )
// Config path (default CONFIG_PATH) - Optional
) Returns( Structure/String/Double )
Returns a the value ( which could be a String or Double) of the Name specified in File. If name is not provided, then a Structure representing the configurations defined in that file is returned.
GetUserCredentials = Func(	src search usage feedback   top
) Returns( String )
Get the user credentials for Secure Database connections. Initialized with Login Credentials. Can be modified with SetUserName call.
LoginName = Func(	src search usage feedback   top
Double( RealLoginNameAsProcmon )
// If someone is using secview as procmon, return their loginname, not procmon's - Optional
) Returns( String )
Retrives LoginName
DbIOSuppressByImplementation = Func(	src search usage feedback   top
SLANG_ARGS( SLANG_ARGS )
// SLANG_ARGS
) Returns( SLANG_RET_CODE )
This function suppresses database i/o within the bound block for
all dbs with the specified implementation. For such dbs, it's as if all
db accesses fail, apart from attach and detach.

'''This is a DANGEROUS function, and you must only use it with care, and if you know what you're doing!'''

SEE ALSO:DbIOSuppressedByImplementation
DbIOSuppressedByImplementation = Func(	src search usage feedback   top
) Returns( SLANG_RET_CODE )
Returns true if I/O is suppressed for this class of db

SEE ALSO:DbIOSuppressByImplementation
SecurityAdd = Func(	src search usage feedback   top
Structure( Values ),
// Values to be set in security
Double( IgnoreWarnings ),
// Boolean to specify whether to ignore validation warnings - Optional
Double( IgnoreErrors ),
// Boolean to specify whether to ignore validation errors - Optional
Double( ReplaceFlag ),
// Boolean to specify whether to replace existing object instances - Optional
Double( CacheOnly )
// Boolean to specify whether to create in cache only - Optional
) Returns( Security )
Adds an instance of a specified Security to the database. Values is transformed to create this object instance The keys and values of Values are set to the VTs and instreams respectively. Values should contain keys such as Security Type and Security Name. These keys specify the object's Security class and the name of the object. All VTs defined in the object should exist in the base Security Class. If they do not exist, an error is displayed instead.
Setting the flags to True has different outcomes.

To Ignore validation warnings set IgnoreWarnings flag to True.
To Ignore validation errors set IgnoreErros flag to True.
To replace existing object set ReplaceFlag flag to True.
To create the object in cache set CacheOnly flag to True.
Note the function modifies objects in the database. Please use with caution when working with Objects in SecDB. In SecDB this function is colored in purple to alert users to be cautious when using this function. The following example adds a Security called _UT A New Script For Testing of type Slang Expression.

Usage
SecurityAdd(Values[, IgnoreWarnings, IgnoreErrors, ReplaceFlag]) The Structure should at a minimum contain the following components and all the required VTs of that instance.
Component Name	Description
Security Type	Name of Security to create the instance. The user should now define the VTs in this Security
Security Name	Name of the newly created Security Instance
Returns
This function returns Null when an error occurs. Errors can happen due to the following:
If the VTs of the Security (instance that you are trying to create) does not match the VTs provided in Values.
If the Security Name (defined in VT Security Type) is not a valid Security.
Example
   Foo = Structure();
   Foo.Security Type = "Slang Expression";
   Foo.Security Name = "_UT A New Script For Testing";
   Foo.Expressiom = "x=4;";
   SecurityAdd( Foo );
See Also
How do I create a SecDb object in a Slang script? , Using Security Add
SecurityAddByInference = Func(	src search usage feedback   top
Structure( Values ),
// Values to be set in security
Double( Flags )
// flags (default is SDB_GET_CREATE) - Optional/Null
) Returns( Security )
Creates an instance of an object class containing the Implied Name VT. This function is similar to SecurityAdd in that it takes a structure (Values) of Value Type names and values. Unlike SecurityAdd, it does not require you to specify a name for your instance. Instead, it relies on SecDb to populate the Implied Name VT. In essence, SecurityAddByInference is a shortcut to the NewSecurity-SetValue-GetByInference method.
Usage
In SecDB this function is colored in purple to alert users to be cautious when using this function. Note that this function modifies objects in the database. Please use with caution when working with Objects in SecDB. The following example adds a Security of type Slang Expression. Unlike SecurityAdd, the name is not provided. The Structure should at a minimum contain the following components and all the required VTs of that instance.

Component Name	Description
Security Type	Name of Security to create the instance. The user should now define the VTs in this Security
Flags
Flags is an optional field that has the following values:
Flag Constant	Description
SDB_GET_CREATE	Instructs SecurityAddByInference to add the security to SecDb if it doesn't already exist
SDB_GET_CACHE_ONLY	Does the same thing as SDB_GET_CREATE to calculate the inferred name. This involves going to SecDb
to find existing securities which have the same inferred name. However, once the inferred name is calculated, there is no more
communication with SecDb. As such, this function does not persist the result of the inference in SecDb and only the cache
is checked for existing securities. Note that this (generally) means it is possible to infer an existing security in the database
due to the implementation of the inference routine and the design of the SecDb deadpool.
In short, this flag is primarily useful if you want to defer persisting your inferred security.

Some pitfalls to watch out for:
- If you infer a new security, and someone persists a security with the same name, you may end up with an error if you try to write your
previously inferred security
- If misused, this can cause holes in the inferred namespace
- If you modify a security after inference, but before persistence you can cause inferred name problems
SDB_GET_CACHE_ONLY_INFERRED_NAME	This flag indicates that you do not want to check SecDb at any point during the SecurityAddByInference operation.
This flag can be dangerous. You should only use this flag if you know the security you are inferring will
never be persisted.
For more info, see What values do I use for the flag parameter of SecurityAddByInference

Returns
This function returns Null when an error occurs. Errors can happen due to the following:
If the VTs of the Security (instance that you are trying to create) does not match the VTs provided in Values.
If the Security Name (defined in VT Security Type) is not a valid Security.
Example
   Foo = Structure();
   Foo.Security Type = "Slang Expression";
   SecuritySecurityAddByInference( Foo );
See Also
Using SecurityAddByInference, How do I create a SecDb object in a Slang script?
SecurityUpdate = Func(	src search usage feedback   top
Security/String( Security ),
// Security to update
Structure( Values ),
// Values to be set in security
Double( IgnoreWarnings ),
// Ignore validation warnings - Optional
Double( IgnoreErrors ),
// Ignore validation errors - Optional
Double( ForceFlag )
// Destroy conflicting object - Optional
) Returns( Double )
Like UpdateSecurity, SecurityUpdate also takes an object (or the name of an object) as its first argument, but requires you to specify a structure of VTs or values to set and update. In this way, you can change a Value Type's contents and update the pertinent SecDb object all at once. Additionally, SecurityUpdate allows you to specify whether to ignore validation warnings and errors on update.
In most cases, you should use SecurityUpdate. You should only use UpdateSecurity if you need to change the contents of a Value Type before updating the database.

Note the function modifies objects in the database. Please use with caution when working with Objects in SecDB. In SecDB this function is colored in purple to alert users to be cautious when using this function.

Returns
This function returns NULL when an error occurs and true otherwise. Errors can happen due to the following:
If the VTs of the Security (instance that you are trying to create) does not match the VTs provided in Values.
If the Security Name (defined in VT Security Type) is not a valid Security
Example
   Foo = Structure();
   Foo.Expressiom = "x=8;";
   SecurityUpdate( "_UT A New Script For Testing", foo);
See Also
Using Setting Values and Updating Objects
SecurityDuplicate = Func(	src search usage feedback   top
Security( Target ),
// Target security
Security( Source ),
// Source security
Double( ValueFlags ),
// Types of ValueTypes to duplicate, SDB_IN_STREAM by default - Optional
Double( SetFlags )
// Set value flags, 0 by default - Optional
) Returns( Double )
Copies data from Source security and assigns the same values to Target security. Both Source and Target must have the same Security Type.
Example
 TC3 = NewSecurity( "Test Class 3", Null );
 SetValue( Ptr1( TC3 ), TC1 );
 SetValue( Ptrs( TC3 ), Security List( [ TC2, TC2, TC3 ] ) );
 TC3D = NewSecurity( "Test Class 3" );
 ret = SecurityDuplicate( TC3D, TC3 );
See Also
What flags should I pass to SecurityDuplicate?
DeadpoolSecurities = Func(	src search usage feedback   top
) Returns( Structure )
Returns a structure of all securities in the current root db deadpool.
Example
 foo =  DeadpoolSecurities();
 Print(foo);
Output
SN DEX00ER31K10       24K104F40: 5
StrTab Class Names             : 2
Structured Note EID            : 4
Structured Note EIT            : 3 
SecurityIsEqual = Func(	src search usage feedback   top
Security( Sec1 ),
// Security 1
Security( Sec2 ),
// Security 2
Double( Flags )
// Flags to match (defaults to SDB_IN_STREAM)
) Returns( Double )
Returns TRUE if Sec1 and Sec2 are equal. The VTs for Sec1 should be the same as the Vts for Sec2. The following compares two securities. The result is 0 (FALSE) since they are not the same.
Example
 bar = GetSecurity("USD/DEM") ;
 bar2 = GetSecurity("USD/CAD");
 SecurityIsEqual(bar, bar2);
SecurityIsNew = Func(	src search usage feedback   top
Security( SecPtr )
// Pointer to the Security
) Returns( Double )
Returns True if the DateCreated VT in SecPtr does not have an assigned value.
See Also
How can I determine if a security exists?
DeleteSecurity = Func(	src search usage feedback   top
String( SecurityName ),
// Name of security to delete
Double( Forcefully )
// Flag to bypass loading of the security. Default is FALSE
) Returns( Double )
Removes a Security from the database and returns True if the security was deleted without problems. The function returns False if it encountered any issues.
Usage
Forcefully is an optional argument that can either be True (to ignore errors on Delete), or False (the default behaviour). Note the function modifies objects in the database. Please use with caution when working with Objects in SecDB. In SecDB this function is colored in purple to alert users to be cautious when using this function.
Example
 //   Delete the "Test Option" security from the database
 If( !DeleteSecurity( "Test Option" ))
 Print( LastError());
See Also
NewSecurity, GetSecurity, RenameSecurity, UpdateSecurity, SetValue, SecDbDeleteByName
DeleteSecurityDuringConflict = Func(	src search usage feedback   top
String/Security( SecurityName )
// Name of security/Security to delete
) Returns( Double )
Usage
This addin can only be called by script "_LIB Analyze Conflicts"
Example
See Also
RenameSecurity = Func(	src search usage feedback   top
Security/String( OldSecurity ),
// Old Security
String( NewName ),
// New Name
Double( Cache Only Inferred Name )
// Optional, default = FALSE
) Returns( Double )
Renames the OldSecurity to NewName and returns True if the Object was successfully renamed and False otherwise. OldSecurity can either be a security object that was loaded using GetSecurity or it can be a Security name.
NewName contains the new name for the security. When it is NULL, the security class determines the name.

Example
 //   Create a new option security, and let the option
 //   security class determine it's name

 Option = NewSecurity( "Option", Null );
 If( Option )
 {
   Today = Current Date( "Security Database" );
   SetValue( Option Style( Option ),      "European" );
   SetValue( Option Type( Option ),       "Call" );
   SetValue( Denominated( Option ),       "DEM" );
   SetValue( Quantity Unit( Option ),     "USD" );
   SetValue( Strike( Option ),                35 );
   SetValue( Expiration Date( Option ),   Today + 7 );

   // Let the option security class pick a name
   if( !RenameSecurity( Option, Null ))
      Print( LastError());
   :
     UpdateSecurity( Option );
  }
:
 Print( LastError());
See Also
NewSecurity, GetSecurity, DeleteSecurity, UpdateSecurity, SetValue, SecDbRename
ReloadSecurity = Func(	src search usage feedback   top
Security( Sec )
// Security
) Returns( )
Reloads Sec object and refreshes it from the database.
If Null is passed in, all objects in the root db are reloaded.
If Sec is a string name, it does GetSecurity( name, SDB_REFRESH_CACHE ) in root db (current db)
When Sec is a security, the following occurs:

If SecurityIsNew( sec ), then nothing happens. This object has not been persisted to secdb thus cannot be reloaded else GetSecurity( name, SDB_REFRESH_CACHE ) in the database where Sec lives.
See Also
GetSecurity, UpdateSecurity , Security Fns
ExistsInDatabase = Func(	src search usage feedback   top
String( Security Name )
// Name of Security
) Returns( Double )
Queries the database to see if a Security (defined by Security Name) exists in the current root database.
Example
 ExistsInDatabase("USD/CAD"); // Value is 1
 ExistsInDatabase("USD/CAD2"); // Value is 0
NameLookup = Func(	src search usage feedback   top
String( SecName ),
// Name to compare against
String( SecType ),
// Class name, Null for all
Double( GetTypes ),
// Get operation type
Double( Count )
// Number of results to return
) Returns( String )
Finds object names in the database based on a search criteria. The criteria is formed by combining SecName, SecType and GetTypes. The SecName argument is used as the base for the search criteria. If SecType is Null, then the function searches all the classes. The following GetTypes are supported:

GetTypes	Description
_Equal	lookup Equal
_First	lookup First
_Ge	lookup Greater than or equal to
_Greater	lookup Greater
_Last	lookup Last
_Le	lookup Less than or equal to
_Less	lookup Less
_Next	lookup Next
_Prev	lookup Prev
Count is an optional argument and is used to cap the number of results returned by the search.

Example
 //   Print out entire list of currencies in reverse order

 For( Name = NameLookup( "", "Currency", _Last ); Name; Name = NameLookup( Name, "Currency", _Less ))
 {
   Print( Name, "\n" );
 };
See Also
ForSecurity, Exist, IndexGet, NameUsed
GetByInference = Func(	src search usage feedback   top
Security( Security ),
// Object created by NewSecurity
Double( CreateFlag )
// True to create if object can't be found
) Returns( Double )
Retrieves or creates a security by inferring it's existence If the object Security cannot be found in the database, GetByInference will try to create, name and add a new object to the database.
This function uses the InferredName name function to determine the name of the object to either load or create. It is useful only for classes that support an inferred name.

Returns
The function returns TRUE if the object is retrieved or created successfully. Under different error conditions it can either return FALSE or NULL.
See Also
GetSecurity, NewSecurity, SetValue, InferredName Handling Securities in Procedural Slang
NewSecurity = Func(	src search usage feedback   top
String( SecType ),
// Type of security to create
String( SecName ),
// Name of the new security, Null for default - OPTIONAL
Array( Args )
// Constructor args - OPTIONAL
) Returns( Security )
Returns a new security of security type SecType with the name specified in SecName. The name must be unique within a database. If SecName is Null, then the name of the security is automatically generated by SecDb. An error is returned if security object SecType does not exists.
Example
 //Create a new option security
 Option = NewSecurity( "Option", Null );
 If( Option )
 {
   Today = Current Date( "Security Database" );
   SetValue( Option Style( Option ),      "European" );
   SetValue( Option Type( Option ),       "Call" );
   SetValue( Denominated( Option ),       "DEM" );
   SetValue( Quantity Unit( Option ),     "USD" );
   SetValue( Strike( Option ),                35 );
   SetValue( Expiration Date( Option ),   Today + 7 );
   UpdateSecurity( Option );
   Destroy( Option );
  }
 :
 Print( LastError());
See Also
GetSecurity, DeleteSecurity, RenameSecurity, UpdateSecurity, SetDiddle, SetValue, SecDbGetByName
GetSecurityFromSyncPoint = Func(	src search usage feedback   top
String( SecurityName ),
// Name of security to get
Double( SyncPointOffset )
// Number of syncpoints to go back - OPTIONAL
) Returns( Security )
Retrieves a previous version of a security. A syncpoint is a copy of the database made at some point in the past. Syncpoints are written on a regular basis. Syncpoints are very useful when restoring deleted or modified objects.
If an object can be retrieved from a syncpoint, the object read from the syncpoint will automatically be renamed to a unique name within the database. This allows for the current version and the syncpoint version of an object to exist simultaneously in memory. The following gets the Security Database object.

Example
 Sec    = GetSecurityFromSyncPoint( "Security Database" );
 Print(Sec);
Output
Security 18 #Sync#
See Also
GetSecurity, SecDbGetFromSyncPoint
UpdateSecurity = Func(	src search usage feedback   top
Security( Security )
// Security to update
) Returns( Double )
Updates a security in the database or creates a new security if the security is not found. This function automatically determines if the security should be added or updated in the database and will fail if the security was updated somewhere else before your call to UpdateSecurity. In other words, if the update by a different app happens between the GetSecurity and UpdateSecurtiy calls, then the application can just re-get the security, make the changes again and then re-update the security. Note the function modifies objects in the database. Please use with caution when working with Objects in SecDB. In SecDB this function is colored in purple to alert users to be cautious when using this function.
Unlike SecurityUpdate, UpdateSecurity takes a security as an argument, and requires you to do a SetValue() first. Note: You should always be using SecurityUpdate()

Returns
False if update fails
Example
 foo = GetSecurity("Test Class B");
 SetValue( Coupon(foo), X );
 UpdateSecurity(foo);
See Also
NewSecurity, GetSecurity, DeleteSecurity, RenameSecurity, SetValue, SecDbAdd, SecDbUpdate
SecDbInsertSecurityRaw = Func(	src search usage feedback   top
Binary( Mem ),
// Binary to use for security
String( Type ),
// Security type
String( Name ),
// Security name
Database( Database )
// Database to insert into
) Returns( Double )
Inserts a transaction given a binary of the security
SecDbCopyNoLoad = Func(	src search usage feedback   top
String( Name ),
// Security name
Database( Source Database ),
// Source Database
Database( Target Database ),
// Target Database
String( New Name ),
// New Name - OPTIONAL
Double( Preserve Disk Info ),
// Whether to preserve Disk Info - OPTIONAL
Double( Preserve DbIDUpdated )
// Whether to reserve DbID Updated - OPTIONAL
) Returns( Double )
Copies an object, as the name suggests, without loading it, by copying the object's binary. This is your best bet when copying objects like trades with dependencies on other securities.
See Also
How do I copy an object from one database to another?
SecDbCopyNoLoadPreservePageTable = Func(	src search usage feedback   top
String( Name ),
// Security name
Database( Source Database ),
// Source Database
Database( Target Database ),
// Target Database
String( New Name ),
// New Name - OPTIONAL
Double( Preserve Disk Info )
// Whether to preserve Disk Info - OPTIONAL
) Returns( Double )
Copies an object, as the name suggests, without loading it, by copying the object's binary. This preserves the Page Table on huge objects after copying. One must then copy the huge page objects explicitly themselves. This is a dangerous function and should be used with care.
SecDbRestoreNoLoad = Func(	src search usage feedback   top
String( Name ),
// Security name
Database( Source Database ),
// Source Database
Double( Offset or transaction id ),
// Source transaction id
Double( Control flag ),
// true to get from syncpoint, false - from transaction id
Database( Target Database ),
// Target Database
String( New Name ),
// New Name - OPTIONAL
Double( Preserve Disk Info )
// Whether to preserve Disk Info - OPTIONAL
) Returns( Double )
Copies a security in binary form from translog or syncpoint. Given a transaction ID it restores the given security under new name.
Note the function modifies objects in the database. Please use with caution when working with Objects in SecDB. In SecDB this function is colored in purple to alert users to be cautious when using this function.

InferredName = Func(	src search usage feedback   top
Security( Security ),
// Security
Double( Cache Only Inferred Name )
// Cache Only Inferred Name - Optional, Default = false
) Returns( String )
Inferred names are essentially hash codes that allow SecDb to quickly identify and share similar securities. SecDb uses the stored information in a security to generate its hash, resolving any collisions through the use of a collision count. Once a security has been written to the database with a name equal to its inferred name, the inferred name should never change. Otherwise, SecDb will no longer be able to identify it using only its stored data. When called on a security, this function returns its inferred name
See Also
NewSecurity, RenameSecurity, UpdateSecurity , Inferred and Implied Names
SecDbNewLoad = Func(	src search usage feedback   top
Structure( Disk Record )
// Disk Record
) Returns( )
Load the object specific information for a new security from an SDB_STORED_OBJECT.
See Also
SecDbLoad
RemoveFromDeadPool = Func(	src search usage feedback   top
String( SecurityName ),
// Name of security to remove (or NULL for all)
Double( Flags )
// SDB_IGNORE_PATH
) Returns( Double )
Removes an unreferenced object, or all unreferenced objects from the deadpool and returns True if it succeeds. The object is specified in SecurityName. If the database has a search path, the reference(s) will be removed from each database in the search path unless SDB_IGNORE_PATH is set.
DeadPools can be considered as caches for recently-used objects. Each time an object is called, the reference counter for that object gets incremented. Each time SecDbFree functions is called for the object, the reference counter for that object gets decremented.

SecurityName can be either a String or Null. If Object is set to Null the entire deadpool is flushed. If the database has a search path, the object is flushed from any deadpool in the path unless the SDB_IGNORE_PATH flag is set.

See Also
GetSecurity, Destroy , 3.1 Security References
AllowSecurityUpdateOnTrade = Func(	src search usage feedback   top
) Returns( )
DEPRECATED Use the functions in Trade APIs to create/update/delete trades so that the correct validations happen, and side-effects are applied. If you are maintaining trade objects, use the APIs in _LIB Trade Update Fns.
Validate = Func(	src search usage feedback   top
Security( Security ),
// Security
*( ReturnedErrors ),
// Returned Errors - Optional
Double( ExecuteSlowValidations ),
// Execute Slow Validations - Optional
Double( ExposeValidationDetail )
// Expose Validation Detail - Optional
) Returns( Double )
Validates a Security by determining if an object considers itself to be valid. Each object within SecDb is required to support a validation message. The meaning of 'valid' is determined by the class of object being validated.
If ExecuteSlowValidations is set to False we skip a number of validations that can only possibly generate a warning.

If ExposeValidationDetail is set to True and the Security is not valid, then ReturnedErros will be a typed structure of type Security Validation::Validate Result.

Returns
True - Object is valid
False - Object is not valid
ValidateVT = Func(	src search usage feedback   top
Security( Security ),
// Security or string
String( VTName )
// VTName
) Returns( Double )
Validates a vt of a security.
InvalidateValue = Func(	src search usage feedback   top
Slang( Value Method )
// InvalidateValue: Argument must be a value method
) Returns( Double )
Clear a Set-Retained value from a security
InvalidateValueIfNotDiddled = Func(	src search usage feedback   top
Slang( Value Method )
// InvalidateValue: Argument must be a value method
) Returns( Double )
Clear a Set-Retained value from a security
GetValue = Func(	src search usage feedback   top
String( value Type ),
// value Type (VT)
String( Security ),
// Security
String( default value )
// default value
) Returns( Any )
Returns a value from the object. Default Value is returned if the VT does not exists, otherwise null is returned.
The most common way to get a value from an object in Slang is through the following syntax example:

 Dollar Price( "Test Option" );
This function provides an alternate method to the one above:

 GetValue( "Dollar Price", "Test Option" );
To summarize it is provided as a convenience for such tasks as:

Getting a table of values from an object.
getting a default value if an object doesn't support the value type.
See Also
SetValue, SetDiddle
GetValueWithArgs = Func(	src search usage feedback   top
String( value Type ),
// value Type (VT)
*( Security ),
// Security
Ellipses( Arguments )
// Arguments
) Returns( Any )
Gets a value for a security. The arguments specified are inputs to the VTs.
Example
 Sec = NewSecurity( "GIR PT Portfolio" );
  Print( LastError() );
  Start Date = RDateAdd( RDate( "-10b" ), Pricing Date( "Security Database" ) );
  End Date = RDateAdd( RDate( "-1b" ), Pricing Date( "Security Database" ) );

  // compound return for 1 company over 10 days of consistent 1% growth is 0.01^5
  Return Value = GetValueWithArgs( "GIR PT Return Value", Sec, "BP.L", Start Date, End Date );
  print(return value);
Output
-0.006157311396
SetValue = Func(	src search usage feedback   top
String/Slang( ValueMethod ),
// Value method (or name) to set the value of
String/Security( Security ),
// Security to act on
Any( Value ),
// Actual value to set value method to
Double( Flags )
// SDB_SET_INTERACTIVE or 0 - Optional
) Returns( Double )
Sets a value of a Security. This function is used to set values within a security. The security should first be loaded or created by using the GetSecurity or NewSecurity functions.
Usage
 SetValue(
    ValueMethod,   // Value method to set the value of
    Value)         // Actual value to set value method to
or

 SetValue(
    ValueMethodName,// Name of value
    Security,      // Security to act on
    Value)         // Actual value to set value method to</tt>
Returns
True if the value was set
False if there was a problem
Example
  // Get the 'Test Option' from the database and update
 //it's strike price

 Option = GetSecurity( "Test Option" );
 If( Option )
 {
   SetValue( Strike( Option ), 35 );
   UpdateSecurity( Option );
   Destroy( Option );
 }
 :
 Print( LastError());
See Also
NewSecurity, GetSecurity, UpdateSecurity
SetValueWithArgs = Func(	src search usage feedback   top
String/Slang( ValueMethod ),
// Value method (or name) to set the value of
String/Security( Security ),
// Security to act on
Array( Args ),
// Arguments to value method
Any( Value ),
// Actual value to set value method to
Double( Flags )
// SDB_SET_INTERACTIVE or 0 - Optional
) Returns( Double )
Set the value of security VT's that are defined SetRetain (typically those defined @Stored or @Retain in the class definition), or are calculated but support a Set handler. SetValue returns True/False, so always check the return value of a Set. There are a number of valid syntaxes you can use:
 rv = SetValue( VT Name( Security ), Value, Flags );
 rv = SetValue( "VT Name", Security, Value, Flags );
and with VT arguments:

 rv = SetValue( VT Name( Security, Arg 1), Value, Flags );
 rv = SetValue( Value Reference( "VT Name" x, Arg1 ), Value, Flags );
 rv = SetValueWithArgs( "VT Name", Security, [ Arg 1 ], Value, Flags );
See Also
Handling Securities in Procedural Slang
SetDiddle = Func(	src search usage feedback   top
String/Value Method( ValueMethodName ),
// Value method to diddle
String/Security( Security ),
// Security to act on
Any( Value ),
// Actual value to diddle value method to
Double( Flags )
// Diddle message flags ( like SDB_SET_NO_MESSAGE ) - OPTIONAL
) Returns( Double )
Diddle values (given in ValueMethodName) within a Security.
This function comes in two flavours:

SetDiddle( ValueMethod, Value [, Flags ] )

or

SetDiddle( ValueMethodName, Sec, Value [, Flags ] )

The function is provided as an alternative to the usual diddle syntax in Slang. The following are equivalent:

 Dollar Price( "DMV1" ) = 100000000;
and
 SetDiddle( "Dollar Price", "DMV1", 100000000 );
This function is useful when the value method name is determined programatically. Both ways of setting diddles have the same scope and are removed by the Restore function or the end of an enclosing Eval block.

Example
 SetDiddle( Value Reference( "Op Add", "Math", 1, 2 ), 4 ); // with args
 SetDiddle( Secdb Node.ValueReference(), 5 );
See Also
Eval, Restore, SetValue, SecDbSetDiddle
ValueTypeDescription = Func(	src search usage feedback   top
String/Slang( ValueMethod )
// Name of value method/value method
) Returns( String )
Returns security valuetype description
Example
 SecName = "TestValueTypeDesc";
 Sec = NewSecurity( "Container: Temp", SecName );
 desc =  ValueTypeDescription( Contents( Sec ) );
 Print(desc);
Output
In-stream value
ValueTypeInfo = Func(	src search usage feedback   top
String/Slang( ValueType )
// ValueType (String or ValueType)
) Returns( String )
Returns global Info about a value type, such as it's Datatype and the ID which it is bound to. This is different from Value Type Info() which returns the class bindings for a ValueType.
Example
 x = ValueTypeInfo( "Price" );
 Print(x);
Output
 DataType: Null
Id      : 111
Name    : Price
ValueTypeChildInfo = Func(	src search usage feedback   top
String/Slang( ValueMethod ),
// ValueMethodNameName of value method/Value Method
String/Slang( Security )
// Name/Pointer of Security
) Returns( Structure )
Returns a structure containing valuetype information of the Child Security
Example
 x = ValueTypeChildInfo( "Table Contents", GetSecurity( "StrTab Day Count ISDA" ) );
 Print(x);
Output
pre> ArgEllipsis : 0 Arguments : CastCount : 0 Casts : ChildDataSize : 16 CycleIsNotFatal : 0 DataType : Array IntermediateCount: 0 Intermediates : LiteralCount : 3 Literals : [ 0] = Table Stored [ 1] = Table Type [ 2] = Table Value Type PassErrors : 0 PullValues : [ 0] = ChildNumber: 1 Offset : 8 SecurityType : String Table TerminalCount : 1 Terminals : [ 0] = Argc : 0 Argv : ArrayReturn: 1 AsObject : 0 Db : Element: 0 Type : SELF Name : Stored PassErrors : 0 Pred true : 1 Predicate : Element: 0 Type : Unknown Result : Element: 0 Type : TERMINAL Security : Element: 0 Type : SELF Unused : 0 ValueType : Element: 0 Type : LITERAL Value : Table Stored
Translation : [ 0] = Stored: Table Stored( Self ) [ 1] = Type: Table Type( Self ) [ 2] = ValueType: Table Value Type( Self ) ValueType : Table Contents

*** LEX-ING FAILED ***

WhiteoutDiddle = Func(	src search usage feedback   top
*( Value Reference )
// Reference to node
) Returns( )
Restores the diddle on this node and all sideffects (if it is a phantom) to the undiddled state. Whiteout diddles are diddles that have no value and thus diddle a node to it's "true" value. e.g. Consider the standard diddle below:
 Eval
 {
     Spot( "JPY/USD" ) = 100;
     Eval
     {
         Spot( "JPY/USD" ) = 110;
         Restore( Spot( "JPY/USD" ) );
         Print( Spot( "JPY/USD" ) );    // Will print 100
     };
 };
So, Restore() removes the innermost diddle, but leaves the outer diddle untouched. A whiteout diddle will diddle the node to have no value, so the Get function is called and the VT is calculated as normal - as if there were no diddle. When the whiteout diddle is restored, the diddles of any encompassing scope will be in place.

 Eval
 {
     Spot( "JPY/USD" ) = 100;
     Eval
     {
         WhiteOutDiddle( Spot( "JPY/USD" ) );
         Print( Spot( "JPY/USD" ), "\n" );       // Prints true value - 103.xxx or similar
         Restore( Spot( "JPY/USD" ) );
         Print( Spot( "JPY/USD" ), "\n" );       // Prints 100
     };
 };
GetCacheFlags = Func(	src search usage feedback   top
String/Slang( Value Method ),
// Value Method or Name
String/Security( Security )
// Security if Name
) Returns( Double )
Returns a double (cache flags) for Value Method for a given Security
Example
 GetCacheFlags("VT Method", "A Security");
SetValueRef = Func(	src search usage feedback   top
String/Slang( ValueMethod ),
// Value Method to set
*( Output variable ),
// Output variable
Double( Set Flags ),
// usual Set Flags - Optional
*( Block )
// Block to modify value
) Returns( )
An alternate way to set the value of a VT
Example
 sec = NewSecurity( "foo" ); // foo has a VT called "my array" that is an Array
 SetValueRef( my array( sec ), a )
  {
      a = [1,2,3,4,5]; // Now value of my array is [1,2,3,4,5]
  };
SecDbGraphClearFailures = Func(	src search usage feedback   top
) Returns( SLANG_RET_CODE )
Clears the cached failures on the specified node and its failed descendants. Invalidates the parents.
See Also
GraphCacheFailures, GraphIsCacheFailuresEnabled
SecDbBuildChildren = Func(	src search usage feedback   top
) Returns( SLANG_RET_CODE )
Builds the first-level children of a given node. Throws on error.
SecDbBuildFullGraph = Func(	src search usage feedback   top
) Returns( SLANG_RET_CODE )
Builds the full graph starting from a given root node and ensures that it is marked TopoValid. Throws on error.
Excel Top
CellAttrRange = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Column ),
// Starting column of range
Double( Row ),
// Starting row of range
Double( Column2 ),
// Ending column of range
Double( Row2 ),
// Ending row of range
Double( Attributes ),
// Attributes for cells
Double( Additive )
// Add to previous attributes - Optional
) Returns( )
Sets the attributes for a range of cells in a sheet. The attributes are defined in CellAttr. This function sets the Cell attributes in Sheet for the range specified by [Row,Column] to [Row2,Column2]
See Also
Sheet, CellAttr, CellFontRange, SheetBox
CellFontRange = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Column ),
// Starting column of range
Double( Row ),
// Starting row of range
Double( Column2 ),
// Ending column of range
Double( Row2 ),
// Ending row of range
Double( FontFace ),
// Typeface of font - Optional
Double( FontSize ),
// Size of font in points - Optional
Double( FontWeight )
// Weight of font - Optional
) Returns( )
Sets the font information for a range of cells in a sheet. The fonts are defined in CellFont. This function sets the Cell fonts in Sheet for the range specified by [Row,Column] to [Row2,Column2]
CellFormatRange = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Column1 ),
// Starting column of range
Double( Row1 ),
// Starting row of range
Double( Column2 ),
// Ending column of range
Double( Row2 ),
// Ending row of range
Double( Decimals ),
// Decimal precision - Optional
Double( Flags )
// SFormatting flags - Optional
) Returns( )
Sets the format within a range of cells in a spreadsheet. The flags are defined in CellFormat. This function sets the precision and the flags in Sheet for the range specified by [Row,Column] to [Row2,Column2] All cells defined in this range get the same precision and flags.
SheetBox = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Column1 ),
// Starting column of range
Double( Row1 ),
// Starting row of range
Double( Column2 ),
// Ending column of range
Double( Row2 )
// Ending row of range
) Returns( )
Draws a box around a group of cells in Sheet. The range is specified by [Row,Column] to [Row2,Column2]
See Also
Sheet, SheetAttr, SheetAttrRange
SheetColumnWidth = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Column ),
// Column number to set
Double( Width ),
// Width of column
Double( StartRow ),
// Starting row - OPTIONAL
Double( EndRow )
// Ending row - OPTIONAL
) Returns( )
This function sets the width of a column in a sheet. The Width parameter is treated as 10ths of an inch when the output is done as postscript. It is treated as characters when the sheet is converted into a string. The default column width is 10 (1 inch.)
Example
 Sheet = Sheet();
 SheetColumnWidth(Sheet,0,2,0,10); // sets the width of the first column to 2 inches
See Also
Sheet, SheetPostscript
SheetRowHeight = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
Double( Row ),
// Row number to set
Double( Height )
// Tenths of an inch
) Returns( )
Sets the height of Row in Sheet.
Example
 Sheet = Sheet();
 SheetRowHeight(Sheet,0,2);
SheetPostscript = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
String( Orientation ),
// Portrait, Landscape, EPS Portrait, EPS Landscape - Optional
String( OutputFile ),
// File/Device name - Optional
Double( AppendFlag )
// Append to destination - Optional
) Returns( )
Outputs a sheet in postscript format by converting a sheet datatype into postscript. The output result is sent to a printer or a file. If OutputFile isn't supplied, the output will be sent to the printer using the 'ps' utility. file. Orientation defaults to Portrait if not supplied. Orientation can be one of the following values:

Values	Description
"Landscape"	Page is horizontally oriented.
"Portrait"	Page is vertically oriented.
"EPS Landscape"	Encapsulated postscript horizontal.
"EPS Portrait"	Encapsulated postscript vertical.
See Also
Sheet
SheetToFile = Func(	src search usage feedback   top
Sheet( Sheet ),
// Spreadsheet to use
String( Destination ),
// File/Device name
String( Format ),
// Tab (default), Comma delimited - Optional
Double( AppendFlag )
// Append to destination - Optional
) Returns( Double )
Converts Sheet to a txt file specified by Destination. The file can be comma separated or tabbed based on Format. By default, this is Tab. If the AppendFlag is supplied, then the data is concatenated to an existing file.
Apply = Func(	src search usage feedback   top
Any( Function ),
// Function Name or Function
Any( Argument ),
// Argument. If there is one positional argument then input the value. If a function has mutliple arguments then an array of values are supplied.
Structure( Named Argument List )
// Named Arguments
) Returns( Any )
Evaluates the input function with the parameters provided. In the examples below, the Function Name or Function is provided in the first param and the arguments for those functions are provided in the second.
Example
 // Using Apply With Built In Functions
   s2 = Apply( "Sprintf", [ "%d %s", 1, "abc" ] ); // Output : 1 abc
   s3 = Apply( "ArrayReverse" , [ [1,2,3,4,5] ] ); // Output : [5,4,3,2,1]

  // Using Apply with Script Functions
 Increment = Func( Double(num) )
 Returns( Double() )
 {
    num++;
    Return(num);
 } ;

 s4 = Apply( Increment, [ 3 ] ); // Output : 4

 // Example 2:
 G = Func( A, B := 0 )
{
    Return( A + B );
};

Assert( Apply( G, 1, NamedArgs := Structure( "B", 2 ) ) == 3 );// Returns true
StatusMessageHook = Func(	src search usage feedback   top
Slang( Hook )
// Hook to call. Of the form: Func( String )
) Returns( )
For Debugging
SlangUninitializedVarHook = Func(	src search usage feedback   top
Slang( Hook ),
// Hook to call. Of the form: Func( Scope, Var ) Return( Value )
String( Scope )
// Scope to which hook should apply. Omit for local scope - Optional
) Returns( )
For Debugging
SlangExpressionGet = Func(	src search usage feedback   top
String( Script Name ),
// Name of Slang Expression
Database( SourceDb )
// SourceDatabase to use - Optional
) Returns( String )
Retrives the script specified in Script Name as a string. If SourceDB is specified then the scripts are retrieved form the the specified database. By default, the SourceDB is DevSource.
Example
 // Get Script from Prod Source
 Expression = SlangExpressionGet( "_LIB STM Utils" , Database("PS") );
SlangExpressionOverride = Func(	src search usage feedback   top
String( Script Name ),
// Name of Slang Expression
Any( Expression )
// Expression to use - Optional
) Returns( )
Overides a script expression with the new expression specified.
CallStack = Func(	src search usage feedback   top
Double( Details )
// Show position details - Optional
) Returns( Array )
Returns an array of all scope names. When Details flag is set to True additional information is retrieved.
Example
 Print( CallStack() ) ;
Output
~
[   0] = (SecViewEvaluate)
[   1] = (Main)
Example
 Print( CallStack(true) );
Output
[   0] = BeginningColumn: 1
BeginningLine  : 1
EndingColumn   : 0
EndingLine     : 2
FunctionName   : (SecViewEvaluate)
ModuleName     : Untitled-6
ModuleType     : 2

[   1] = BeginningColumn: 0
BeginningLine  : 0
EndingColumn   : 0
EndingLine     : 0
FunctionName   : (Main)
ModuleName     :
ModuleType     : 0 
GetExecutionContexts = Func(	src search usage feedback   top
) Returns( Array )
Returns an array of Call Stacks, one for each active execution context. The first entry in the array is always the current execution context.
SlangCallStackAllThreads = Func(	src search usage feedback   top
) Returns( Array )
Returns an array of Call Stacks, one for each Slang thread. The first entry in the array is always the call stack for the currently active thread.
SecDbGetNodeStack = Func(	src search usage feedback   top
) Returns( Array )
Returns the current SecDb Node Stack (for debugging)
CurrentFunctionName = Func(	src search usage feedback   top
) Returns( String )
Returns the name of the current slang function.
Example
 foo = func()
 {
   print( CurrentFunctionName() );

 };

 @foo();
Output
foo
Scope = Func(	src search usage feedback   top
String( ScopeName ),
// Name of scope or call depth
String( VarName )
// Name of variable
) Returns( )
Returns a reference to variable within scope.
The :: operator is used to conveniently reference variables from within a scope. This function differs from the :: operator in that the VarName argument is actually a variable itself, while :: takes only constant string expressions.

The usage of the :: operator and Scope function is as follows:

 Global::Foo = 10;
 Print( Scope( "Global", "Foo" ), "\n" );
 NewScope::Var1 = CurrentTime();
 Scope( "NewScope", "Var2" ) = CurrentGmTime();
See Also
Scopes
Variables = Func(	src search usage feedback   top
String( ScopeName )
// Name of scope or call depth
) Returns( Array )
Retrieves a list of variables within the scope provided by ScopeName. This function returns an array of the variable names that are defined within a scope.
Example
 //Print the list of variables defined in the global scope
 Print( Variables( "Global" ));
See Also
Scope, Scopes
SlangPosition = Func(	src search usage feedback   top
Double( Scope )
// stack depth to return position info from - Optional
) Returns( Structure )
Returns info on the current cursor position.
Example
 Print(SlangPosition());
Output
BeginningColumn: 7
BeginningLine  : 1
EndingColumn   : 22
EndingLine     : 1
Module         : Untitled-6
Structures Top
ForComponent = Func(	src search usage feedback   top
*( Component ),
// Loop variable that will hold Container's keys.
*( Container )
// The Structure to iterate through.
) Returns( )
Iterates through all the keys (components) in a Structure, GStructure, or Typed Structure. Keys are retrieved in alphabetical order, regardless of how they were originally populated. For example, in the code below, ForComponent will first retrieve Age and then Name. To access the value for a particular key, index Container on the key's name (i.e., call Container[key]).
You can optionally use a datatype or datatype+spec on the iterator variable: see Slang Specs: How do I establish preconditions and postconditions on function arguments and return values?

Usage
If desired, you can pass an Array to ForComponent. In this case, the function will iterate over the Array's indices (e.g., 0, 1, and 2 for the Array ["apple","banana","cherry"]).
Example
The following example iterates through a Structure and prints out its keys and values.
 Struct = Structure();
 Struct["Name"] = "John Smith";
 Struct.Age = 20;

 ForComponent( Key, Struct )
     Print( Key, " = ", Struct[ Key ], "\n" );
Output
Age = 20
Name = John Smith
 // And now with datatype+spec
 ForComponent( String( ObjName, Spec::String( Max Size := 31 ) ), Struct )
     Print( ObjName, "\n" );
See Also
ForEach , Structure
ComponentExists = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag )
// Search Tag
) Returns( Double )
Searches Container and checks whether the key defined by Tag resides in the Container. If Tag exists then True is returned, else False is returned. This search is case insensitive. For example, the input Struct containing Grass is passed to ComponentExists(Struct, "GRASS"). The function outputs True even though the cases of the key and the Tag differ.
Usage
This is widely used for testing the existence of keys within a Structure and can be combined with conditionals such as If and While
Example
The following example searches for keys within Struct
 Struct = Structure();

 Struct["Grass"]   =  "Green";
 Struct["Sky"]     =  "Blue";
 Struct["Tar"]     =  "Black";

 Value_True  = ComponentExists(Struct , "GRASS");
 Value_False = ComponentExists(Struct , "Sun");

 Print(Value_True + "\n");
 Print(Value_False + "\n");
Output
1
0
ComponentExistsStrict = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag )
// Search Tag
) Returns( Double )
Similar to ComponentExists. The difference between this method and ComponentExists is that if the Container does not exist or does not support component extraction (i.e. at run time ) then the users will be alerted with a red box containing an error message.
Example
 Foo = 5;;

 r = ComponentExistsStrict( Foo, "USA" );

 r = ComponentExistsStrict( Undefined, "Mexico" );
Output
Both calls will redbox
ComponentTestAndGet = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag ),
// Search Tag
Any( Value )
// The value returned from the Container whose key is Tag
) Returns( Double )
Allows users to access the value associated to the the key Tag within a Container. The Container is an enumerable datatype which contains many pairs of keys and values. This function searches the Container for the key Tag and retrieves the associated value of that key.
Note: Like ComponentExists the search for the key is case insensitive.

Returns
Return Value	Description
True	Returns True if the container contains the key Tag.
The associated value is stored in Value.
False	Returns False if the container does not contain the key Tag.
In this case, the variable Value will not have its current
contents overriden.
Example
The following example retrieves the value for the key USA. It also tries to retrieve the value for the key Mexico. Since this key does not exists, the value of result remains unaltered.
 Foo = Structure();

 Foo["USA"]    = "USD" ;
 Foo["Canada"] = "CAD" ;
 Foo["UK"]     = "GBP" ;

 r = ComponentTestAndGet(Foo, "USA", result);
 Print("r is " + String(r) + " result is " + result);
 r = ComponentTestAndGet(Foo, "Mexico", result);
 Print("r is " + String(r) + " result is " + result);
Output
r is 1 result is USD
r is 0 result is USD
ComponentGetStrict = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag ),
// Search Tag
*( Value )
// The value returned from the Container whose key is Tag
) Returns( Double )
Similar to ComponentTestAndGet, allows users to access the value associated to the the key Tag within a Container. The Container is an enumerable datatype which contains many pairs of keys and values. This function searches the Container for the key Tag and retrieves the associated value of that key. The difference between this method and ComponentTestAndGet is that if the Container does not exist or does not support component extraction (i.e. at run time ) then the users will be alerted with a red box containing an error message.
Example
 Foo = 5;;

 r = ComponentGetStrict( Foo, "USA", result );

 r = ComponentGetStrict( Undefined, "Mexico", result);
Output
Both calls will redbox
ComponentExtract = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag ),
// Search Tag
Any( DefaultValue )
// The value returned if the Container doesn't have the key Tag.
) Returns( SLANG_RET_CODE )
Allows users to access the value associated to the the key Tag within a Container. The Container is an enumerable datatype which contains many pairs of keys and values. This function searches the Container for the key Tag and retrieves the associated value of that key.
Note: Like ComponentExists the search for the key is case insensitive.

Returns
Return Value	Description
Value	Returns Value if the container contains the key Tag with the associated value Value.
Default Value	Returns Default Value if the container does not contain the key Tag
Example
 Foo = {| a := 1, b := 2 |};

 Value a = ComponentExtract( Foo, "a", 0 );
 Value b = ComponentExtract( Foo, "b", 0 );
 Value c = ComponentExtract( Foo, "c", 0 );
Output
Value a is 1
Value b is 2
Value c is 0
ComponentExtractStrict = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Tag ),
// Search Tag
Any( DefaultValue )
// The value returned if the Container doesn't have the key Tag.
) Returns( SLANG_RET_CODE )
Similar to ComponentExtract. The difference between this method and ComponentExtract is that if the Container does not exist or does not support component extraction (i.e. at run time ) then the users will be alerted with a red box containing an error message.
Example
 Foo = 5;

 r = ComponentExtractStrict( Foo, "USA", 0 );

 r = ComponentExtractStrict( Undefined, "Mexico", 0 );
Output
~ pre> oth calls will redbox /pre>
ComponentEnsure = Func(	src search usage feedback   top
*( Container ),
// Container of a subscriptable type, e.g. Structure, GStructure, Array.
*( Key ),
// Component Key
Any( InitialValue )
// The value that Container[ Key ] is set to if it doesn't exist
) Returns( SLANG_RET_CODE )
Returns component Key of Container (as an Lvalue if needed); if the component does not exist, creates one with the value of InitialValue. InitialValue is only evaluated if the component does not exist.
ComponentReplace = Func(	src search usage feedback   top
*( Container ),
// Container to replace a component in
*( Key ),
// Component Key
Any( Value )
// The value that Container.Key is set to
) Returns( SLANG_RET_CODE )
Replaces the component Key of Container with Value.
Differs from Container[Key] = Value on data types which treat subscripts (A[B]) and components (A.B) differently (e.g. SlangType-based ones).

ForComponentValue = Func(	src search usage feedback   top
*( Component ),
// Loop variable which holds the Container's key during each iteration.
*( Value ),
// Loop variable which holds the Container's value during each iteration.. Use &Var to get a modifyable value
*( Container )
// An enumerable value. (Componet,Value) will be set to each (key,value) in the container
) Returns( )
Iterates through all the keys (components) in a Structure, GStructure, or Typed Structure and retrieves the keys and values. The .keys() sorts the data regardless of how they were originally populated. The loop variable Value holds the value during each iteration. This allows the users to access the value directly without referencing the Container.
Value can be passed in by reference or by value. When Value is passed in by reference, modifications to Value will also update the contents of Container. In this case, the old value (for a key) will be replaced with the newly modified value.

Note: When iterating through a GStructure using ForComponentValue, the keys retrieved are not sorted. However calling .keys() on GStructure does sorts the keys.

Example
The following example displays the uses of ForComponentValue:
 // Case when this Container is a Structure
 Foo = Structure();
 Foo.A = "AA";
 Foo.B = "BB";
 Foo.C = "CC";

 ForComponentValue(Key, Value, Foo)
     Print( "The Key is ", Key, " and the value is ", Value, "\n" );
Output
The Key is A and the value is AA
The Key is B and the value is BB
The Key is C and the value is CC
 // And now with datatype+spec
 ForComponentValue( String( ObjName, Spec::String( Max Size := 31 ) ), Double( ObjSize, Spec::Integer() ), ObjNames )
 {
     Print( ObjName, "\t", ObjSize, "\n" );
 };

 // Case when the container is a Typed Structure
 TypeDefine( "Bar" )
 {
     Members()
     {
         String( Field1 ) := "I am Field One",
         String( Field2 ) := "Field Content"
     }
  };

 TS = Typed Structure( "Bar" );

 ForComponentValue(Key, Value, TS)
     Print( "The Key is ", Key, " and the value is ", Value, "\n");
Output
The Key is Field1 and the value is I am Field One
The Key is Field2 and the value is Field Content
StructureFromKeys = Func(	src search usage feedback   top
Array( Keys ),
// Array of keys
Array( Values ),
// Array of values
Double( CastToStringKeys )
// The default is False. A boolean used to convert non-string keys to strings
) Returns( Structure )
Creates a datatype of Structure/StructureCase from a list of keys and values specified in Keys and Values. This is another way for creating Structure/StructureCase. Note: the size( Keys ) must equal the size( Values ). If Values contain a single element, then this value is used to initialize every key in the datastructure.
Parameters
CastToStringKeys is a boolean to indicate the conversion of non-string keys to string keys. By default, this attribute is False and all keys defined should be of type String. When this attribute is set to True, any numeric keys will be converted to its string equivalent.
Example
 Keys = [ "Cow", "Cat", "Pig" ];
 Values = [ "Moo", "Mew", "Oink" ];
 Foo = StructureFromKeys( Keys, Values );

 Foo_S = Structure();
 Foo_S.Cow = "Moo";
 Foo_S.Cat = "Mew";
 Foo_S.Pig = "Oink";

 Assert( Foo == Foo_S );
GStructureFromKeys = Func(	src search usage feedback   top
Array( Keys ),
// Array of keys
Array( Values )
// Array of values
) Returns( GStructure )
Creates a datatype of GStructure from a list of keys and values specified in Keys and Values. This is another way for creating GStructure. Note: the size( Keys ) must equal the size( Values ). If Values contain a single element, then this value is used to initialize every key in the datastructure.
Example
 Keys = [ "Cow", "Cat", "Pig" ];
 Values = [ "Moo", "Mew", "Oink" ];
 Foo = GStructureCaseFromKeys( Keys, Values );

 Foo_S = GStructure();
 Foo_S.Cow = "Moo";
 Foo_S.Cat = "Mew";
 Foo_S.Pig = "Oink";

 Assert( Foo == Foo_S );
Structure = Func(	src search usage feedback   top
Array( Contents )
// Array consisting of a pair of key,value pairs. It is indexed by key
) Returns( Structure )
A Structure is a datatype that stores many pairs of keys and values. It can be considered as a Hashtable containing keys and values associated to those keys. Keys are required to be of datatype String and values can be Any datatype. Since keys are of type String, they can have multiple words. For example, the word "Three Word Key" qualifies as a valid key for a Structure.
Users can access the value for a key by using the '.' operator followed by the key name (example Struct.Key). You can also indexing the Structure by key name. For example, Struct["Three Word key"] would retrieve the value associated to this key.

Note, the word key and component can be used interchangeably. It is common to refer to key in Slang as component.

Usage
The following lists the different ways a Structure can be created:
 a = Structure();
 a = New( "Structure" );
 a = Structure( "Tag1", Value1, ... "TagN", ValueN );
Once a Structure has been created, keys and values can be set as follows:

 a.Name     = "Demo Name;
 a.Location = "New York;
 a.Hours    = 8;
 a.Points   = [ 1, 2, 3, 4 ];
Another way to get/set components within a Structure is to use the subscript operator ([]). Note that this syntax is processed about 25% slower than the dot (.) notation, so should only be used when including a variable as a Structure key. For example:

 var = "Points";
 Print( a[ var ] );
Subscript and Component Operators
Struct.Component
Struct[ "Component" ]
Functions
Function Name	Description
ForComponent	Loops through the Structure giving a pointer to the key
ForComponentValue	Loops through the Structure giving a pointer to the value
ForEachComponent	Loops through the Sructure giving a pointer to the key
ComponentTestAndGet	Gets the value assigned to the key
ComponentExists	Checks a Structure given a key/component
Size()	returns the number of components in the Structure
Operators
Operators	Description
Struct1 + Struct2	Add contents of both Structures
Struct1 - Struct2	Subtract contents of 2 from 1
Struct1 * Struct2	Multiply contents of both Structures
Struct1 / Struct2	Divide contents of 1 by 2
Struct1 + AnyValue	Add AnyValue to each component
Struct1 - AnyValue	Subtract AnyValue from components
Struct1 * AnyValue	Multiply each component by AnyValue
Struct1 / AnyValue	Divide each component by AnyValue
Assignment Operators
Assignment Operators	Description
Struct1 += Struct2	Add contents of both Structures
Struct1 -= Struct2	Subtract contents of 2 from 1
Struct1 *= Struct2	Multiply contents of both Structures
Struct1 /= Struct2	Divide contents of 1 by 2
Struct += AnyValue	Add AnyValue to each component
Struct -= AnyValue	Subtract AnyValue from components
Struct *= AnyValue	Multiply each component by AnyValue
Struct /= AnyValue	Divide each component by AnyValue
Compare Operators
Compare Operators	Description
Struct1 == Struct2	Contents of Structures equal
Struct1 != Struct2	Contents of Structures not equal
StructureStatistics = Func(	src search usage feedback   top
Structure( InputStruct )
// Structure that will be used to query for statistics
) Returns( Structure )
Returns statistics about the memory usage of InputStruct.
Example
 Foo = Structure( ["A", "1" , "B", "2", "C", "3"] );
 Stats = StructureStatistics( Foo );

 ForComponentValue( Key, Value, Stats )
    Print( String( Key ), " : ", String( Value ), "\n" );
Output
Actual Delete Count : 0
Actual Key Count : 3
Buckets : 11
Chain Length StdDev : 0
Delete Count : 0
Has Copy Func : 1
Has Destroy Func : 1
KeyCount : 3
Longest Chain Length : 0
Mean Chain length : 0
Reference Count : 2
Sanity Check Result : 1
Usability : 1
SysNCon = Func(	src search usage feedback   top
String( Command )
// Command string
) Returns( Double )
System() without creating a console window on Windows
System = Func(	src search usage feedback   top
String( Command )
// Command string
) Returns( Double )
Executes an operating system Command that is passed in. The function waits for the command to finish, and then returns the result. Note that on Linux and other Unix-like systems, the result is a bitfield containing the exit status, the number of the signal that killed the process, etc. If you want this information decoded from the result, use SystemDecode instead.
Example
 //   Print a 'Yow' message

 Check( 0 == System( "yow > yow.tmp" ) );
 File = FileOpen( "yow.tmp" );
 While( Line = FileReadLine( File ))
      Print( Line, "\n" );
 Destroy( File );
 System( "del yow.tmp" );
AccessViolate = Func(	src search usage feedback   top
) Returns( )
This will bring up the just-in-time debugger. Note: This is for debugging purposes and should be used with caution. Supported arguments are:
None: will cause segv due to null pointer dereference
1: will cause stack overflow due to infinite recursion
2: will cause segv due to corruption of stack
CPPException = Func(	src search usage feedback   top
Double( ExceptionType )
// CPP_EXCEPTION_TYPE value
) Returns( )
Throws a C++ exception of the specified CPP_EXCEPTION_TYPE for testing the evaluator's exception handling.
SlangXProcessDieWithParent = Func(	src search usage feedback   top
) Returns( )
Controls whether this process will die when its parent process goes away; returns True if setting updated successfully, otherwise False. Only implemented on Linux.
Shutdown = Func(	src search usage feedback   top
Double( Reboot ),
// TRUE to reboot after shutdown (default) - Optional
String( Message ),
// Message to display in dialog box - Optional
Double( Timeout ),
// Seconds to display dialog box - Optional
Double( Force ),
// TRUE to force apps closed even with unsaved changes (default) - Optional
Double( Computer )
// Name of computer to shut down (Null for your own) - Optional
) Returns( )
System call to shut down a computer. The options specified in the parameters will act as defined. Forexample, Shutdown(TRUE,"Shutting down comp", 10, FALSE), will do the following:
Display a message "Shutting down comp" for 10 sec
Ask the user to save unsaved data
And finally reboot the machine
ShowStack = Func(	src search usage feedback   top
) Returns( )
Prints out the current state of stack. Note: This does not work properly. Avoid usage.
ThreadID = Func(	src search usage feedback   top
) Returns( Double )
Transaction Top
TransLogLast = Func(	src search usage feedback   top
) Returns( Double )
Retrieve the number of the last transaction in the database. This number can be used to run backwards through the transaction log looking for transactions of interest.
Example
 // Print the last transaction id
 Print( TransLogLast() ); //  254552058
TransLogHeader = Func(	src search usage feedback   top
Double( TransID )
// Transaction ID
) Returns( Structure )
Retrieve the header associated with a transaction. Any time a database is modified (something added, deleted, modified, index built, etc.) a transaction is created. A transaction consists of a header and detail. The header record contains general information about the transaction and can be obtained by using this function. TransLogDetail retrieves the detail portion of a transaction, the detail contains the actual list of the actions that modified the database.
Returns
The returned structure consists of the following components:

Name	Description
Allow Async Transaction	Boolean to indicate async transaction.
Application Name	Name of the application that added the transaction.
Database	Database where the transaction was initially created. This is usefull when dealing with synchronized databases.
Detail Bytes	Number of bytes in the transaction detail record.
Detail Key1	Key used by the database driver.
Detail Key2	Key used by the database driver.
Detail Parts	Number of parts in the detail record. Each part corresponds to a structure in the array returned by TransLogDetail.
GM Time	Greenwich Mean Time that the transaction was added.
Network Address	IP address of the machine that added the transaction. Some database drivers do not support this field.
SecName	Description of the transaction.
SecType	Optional security type.
Source Trans ID	If the transaction came from a synchronized database, then this field will contain the transaction ID from the original database.
Trans ID	Transaction ID of this transaction.
Trans Type	Type of transaction (detailed below)
Type	Commit/Abort
User Name	Name of the user who committed the transaction.
Example
 TransLogLast = TransLogLast();
 TransLogHeader = TransLogHeader( TransLogLast );
Output
Allow Async Transaction: 0
Application Name       : SecView
Database               : !NYC_Snap
DbId                   : 722
Detail Bytes           : 2574
Detail Key1            : -1
Detail Key2            : 0
Detail Parts           : 12
GM Time                : Mon  4Jun07 09:30:01 am
Login Name             : KERBIDX
Network Address        : 111.22.333.444
NetworkAddress         : 131313131
secName                : FOOBAR
SecType                :
Source Trans ID        : 0
Trans ID               : 254552046
Trans Type             : Begin
TransFlags             : 0
TransType              : 0
Type                   : Commit
User Name              : KERBIDX
TransLogDetail = Func(	src search usage feedback   top
Double( TransID ),
// Transaction ID
Double( RawMemory )
// Raw Dump Flag - Optional. False by default
) Returns( Array )
Any time a database is modified (something added, deleted, modified, index built, etc.) a transaction is created. A transaction consists of a header and detail. The header record contains general information about the transaction and can be obtained by using the TransLogHeader function. The TransLogDetail function retrieves the detail portion of a transaction, the detail contains the actual list of actions that modified the database.
The TransLogDetail function returns an Array of Structures. Each Structure corresponds to an event within the transaction that modified the database.

RawMemory is a flag used to indicate whether the function should parse the object's binary data into a Structure of instream values. Possible values are as follows,


_MEM_FULL	The memory is returned as a fully expanded Structure.
_MEM_RAW	The memory is returned as raw binary data.
_MEM_NONE	The memory is not returned at all.
The default behavior is identical to _MEM_FULL. This extra processing can slow evaluation. To optimize performance, pass _MEM_RAW or _MEM_NONE.

Each Structure returned by TransLogDetail can have one or more of the following components,


Name	Descriptiom
OldSdbDisk	Structure of old object's disk information.
Stored Object	Structure/Memory block containing the object's instream values. If the RawMemory argument is set to True, a block of memory will be returned. Otherwise, a Structure of the object's instream values will be returned.
Index Name	Name of index.
Part Count	Number of parts in an index update.
SecName	Name of object..
Type	Type of operation
Values	Table of values in an index update.
Direction	Direction of an incremental update.
Msg Mem	Memory block passed to the server's incremental function.
Msg Mem Size	Size of the memory block passed to a server's incremental function.
SdbDisk	Structure containing the object's disk information
TransLogObjects = Func(	src search usage feedback   top
Double( TransID ),
// Transaction ID
Double( Details )
// If TRUE, ( Type, SdbDisk, Mem, PriorTransaction )
) Returns( Array )
TransLogSecTypes = Func(	src search usage feedback   top
Double( TransID )
// Transaction ID
) Returns( Array )
Return an Array of the security types of the securities modified by transaction, TransID, in the current database.
TransactionCurrent = Func(	src search usage feedback   top
Double( Memory )
// Memory Dump Flag
) Returns( Array (or Null on error) )
Get current uncommitted transaction
The optional Memory Dump Flag argument controls how the in-memory representation of the transaction is returned:


Flag	Description
_MEM_FULL	The memory is returned as a fully expanded Structure.
_MEM_RAW	The memory is returned as raw binary data.
_MEM_NONE	The memory is not returned at all.
The default behavior is identical to _MEM_FULL.

TransactionSize = Func(	src search usage feedback   top
Database( Database )
// Database - Optional
) Returns( Double )
Return size of binary in current uncommitted transaction
Transaction = Func(	src search usage feedback   top
String( Name ),
// the name that will appear in the Transaction log for this Transaction (SecName in the TransLog header)
Double( Force ),
// a positional optional flag to Force the Transaction
Double( ReturnTransactionID )
// a positional optional argument to get the Transaction ID returned (if succesful - zero otherwise)
) Returns( Double )
This function is used to ensure that all database operations within a block commit or fail together. This prevents two or more operations that depend on one another to be out of sync. The TransactionAbort function can be used within the block to abort the transaction, exit the block, and return False from Transaction. The Transaction function can be nested.
The Force flag should not be used unless you know what it does - it probably does not do what you think.

The use of TransactionCommit within a Transaction block will mean that the Transaction can no longer be guaranteed to be atomic.

If the Transaction does not actually persist anything, but does not in any other way fail, the Return value will still be True. If the ReturnTransactionID flag has been used, the return value will be 1 (True) as no Transaction will actually exist in the database.

Transactions cannot be atomic across Physical Databases. A UseDatabase to a differnet Physical Db (even in the same Ring) inside a Transaction block will result in brand new Transaction(s) in the Database switched to with a SecName of the Securities (not the Name set by this Func). If a Security was loaded from a different Database to the Database of the Transaction, UpdateSecurity will result in a seperate Transaction in that loaded-from Database (also with SecName defaulting to the name of the Security). Neither of these syntaxes will error.

An example of transactional protection can be found in the implementation of trades. A trade will update one or more positions. The positions must be updated along with the trade for the database to remain consistant.

Example
 // Delete two securities (or none if either can't be deleted)

     Success = Transaction( "Demo Transaction" )
     {
         DeleteSecurity( "Bogus 1" );
         DeleteSecurity( "Bogus 2" );
     };

     If( Success )
         Print( "Securities deleted without error" )
     :
         Print( "Couldn't delete because:\n", LastError());


 // Find the TransactionID for what was just done

     UseDatabase( Database( "Snap" ) )
         TransID = Transaction( "Update Test", , True )
             UpdateSecurity( GetSecurity( "moontg" ) );

     Print( TransID, "\n" );
TelemetryTransaction = Func(	src search usage feedback   top
String( Name )
// the name that will appear in the Transaction log for this Transaction (SecName in the TransLog header)
) Returns( Double )
TelemetryTransaction provides a facility for composing telemetry transactions. Telemetry transactions are identified with the SDB_TRAN_FLAG_TELEMETRY_TXN bit set in their Trans Flags. Telemetry transactions are constrained in that they may only contain one insert part of a nonextant Transaction Telemetry security followed by its deletion. TelemetryTransaction is only intended for use in SecDBA applications. If you have a need outside of this please consult with SecDBAs.
Example
 Success = TelemetryTransaction( "Transaction Telemetry" )
 {
     Sec Name = Sprintf( "NOOP %s", @GSUID Short::Generate() );
     CheckE( SecurityAdd( {| Security Type := "Telemetry Details", Security Name := Sec Name |} );
     Check( DeleteSecurity( Sec Name ) );
 };

 If( !Success )
    Throw( ErrMore( "Failed TelemetryTransaction" ) );
TransactionAsync = Func(	src search usage feedback   top
String( Description )
// Description of this transaction.
) Returns( )
TransactionAsync() can be used in place of Transaction() when you need to commit a LARGE ATOMIC transaction. If your transaction is not large, you should use Transaction() because sychronized transactions are less likely to cause update conflicts. If your transaction need not be atomic, use Transaction() with intermitent TransactionCommit() calls. Within a TransactionAsync() block, TransactionCommit() is disallowed. Unlike Transaction(), you cannot 'force' TransactionCommit() to convert regular updates into pairs of delete/insert. Async transactions can be used in combination with normal transactions. Async Transactions can be nested inside or outside normal tranasction. The outermost transaction determines the async/non-async behavior.
TransactionCommit = Func(	src search usage feedback   top
Double( Parts Threshold ),
// Commit if more parts than this (-1 for no limit, defaults to 100) - Optional
Double( Size Threshold ),
// Commit if bigger than this (approx, bytes) (-1 for no limit, defaults to 30k) - Optional
Double( Force )
// Force transaction - Optional
) Returns( Double )
Commits and starts a transaction if the current transaction exceeds Parts Threshold parts or Size Threshold (bytes).
Works like TransactionAbort() if it fails - that is, the remainder of the Transaction is aborted.

Must only be called within a Transaction() block, but has no effect except at the topmost level.

Returns True if transaction was committed, else False.

If TransactionCommit is invoked within a TransactionAsync block, it will abort transaction at current level, and return false.

IMPORTANT CAVEAT Only use this if you are bundling transactions for efficiency. You MUST not use it if you are relying on the transaction being committed in an atomic operation.

The Force flag should not be used unless you know what it does - it probably does not do what you think.

TransactionAbort = Func(	src search usage feedback   top
String( Error Text ),
// Error Text - Optional
Double( Error Code )
// Error Code - Optional
) Returns( Double )
Aborts a Transaction that is in progress
TransMap = Func(	src search usage feedback   top
) Returns( Array )
Returns the current server's transaction map
Types Top
TypeForward = Func(	src search usage feedback   top
String( TypeName ),
// Name of the type
Double( ConstructorIsEvalOnce )
// Optional
) Returns( )
Registers a type structure at parse-time, and links it with a dummy message dispatcher function.
Example
 TypeForward( "Bar::Foo", True );
TypeDefine = Func(	src search usage feedback   top
String( TypeName ),
// Name of the type
Double( ConstructorIsEvalOnce )
// Optional
) Returns( )
Constructor for defining a non-streamable type. Non-streamable types can not be saved to streams or objects. Note: Scope and Name must be different, otherwise, secview may crash.
Example
 TypeDefine( "Scope::Name" )
 {
    [_Super = Null; ]                  // optional, to use @_Super
    ... statics                        // varName = value; , no typing
    ... functions (Func, Lambda) ...   // only Lambdas can access statics and use Super
    Members( [ BaseType ] )            // Optional Base Type for inheritance
    [ Implements( Interface, ... ) ]   // Optionally Implement an interface
    {
     ....
    };
  };
TypeDefineInterface = Func(	src search usage feedback   top
String( TypeName )
// Name of the type
) Returns( )
Define an interface. Typed Structure Interfaces are very similar to Java interfaces.
Example
 TypeDefineInterface( ... )
 {
   ... functions ...
   Extends( InterfaceName, ... );  // Extends() is Optional
 };
See also Typed Structure FAQ.

TypeDefinePackage = Func(	src search usage feedback   top
String( TypeName )
// Name of the type
) Returns( )
Define a Typed Structure Package. A package is a non-streamable type containing functions and a ContractMembers() block only. It is a convenient way to package member functions and import them by various types.
Example
 TypeDefinePackage( ... )
 {
   ... functions ...
 };
See also Typed Structure FAQ.

TypeDeclare = Func(	src search usage feedback   top
Double( TypeID ),
// Type ID used to stream this type.
String( TypeName )
// Name of the type
) Returns( )
Defines a streamable type. Streamable types can be saved as Value Types of objects. They require a unique ID.
Example
 TypeDeclare( TypeID, "Scope::Name" )
  {
    ... everything the same as TypeDefine
  };
TypeInfo = Func(	src search usage feedback   top
String( TypeName ),
// Name of type for which to get info - Optional
Double( LoadType )
// Pass False to prevent initializing type
) Returns( )
Returns structure of info for the type. If LoadType is False, returns a structure with only basic info: Name, TypeLib and TypeId. Omit TypeName to have it return an array of names of types initialized in this session."
TypeInfoByID = Func(	src search usage feedback   top
Double( TypeID ),
// ID of type for which to get info
Double( LoadType )
// Pass False to prevent initializing type - Optional
) Returns( )
Returns structure of info for the type id. If LoadType is False, returns a structure with only basic info: Name, TypeLib and TypeId.
TypeUndefine = Func(	src search usage feedback   top
String( TypeName )
// Name of type to undefine
) Returns( )
TypeLink = Func(	src search usage feedback   top
Double( TypeId ),
// Type ID used to stream this type.
String( TypeName ),
// Name of the type
String( TypeLib ),
// Name of the type defining script
Double( ConstructorIsEvalOnce )
// Whether the constructor is marked eval once - Optional
) Returns( )
Registers a streamable typed structure, and makes it available globally. This is usually defined in _LIB Typed Structure DeclXXXX as:
 TypeLink( 2749, "Insurance::Life Data", "_TYPE Insurance Life Data" );
TypeLinkDeprecated = Func(	src search usage feedback   top
Double( TypeId ),
// Type ID used to stream this type.
String( TypeName ),
// Name of the type
String( TypeLib ),
// Name of the type defining script
Double( DatatypeId ),
// Actual datatype id
Double( ConstructorIsEvalOnce )
// Whether the constructor is marked eval once - Optional
) Returns( )
Op = Func(	src search usage feedback   top
Slang( Expression )
// x BinOp y
) Returns( )
SlangXWinProcessCreate = Func(	src search usage feedback   top
String( Command )
) Returns( Double )
SlangXWinProcessExitCode = Func(	src search usage feedback   top
) Returns( Double )
SlangXWinProcessJoin = Func(	src search usage feedback   top
) Returns( Double )
================================================================================
String Functions (not in auto-generated SLAM - added manually)
================================================================================

StrPos = Func(
    String( String ),
    // String to search
    String( SubString ),
    // String to search for
    Double( Start )
    // (Optional, Default = 0) Starting offset in String
) Returns( Double )
Position of SubString within String (0-based). Returns -1 if not found.

Example:
    StrPos( "hello~world", "~" )    // returns 5
    StrPos( "abcabc", "bc", 2 )    // returns 4 (search from offset 2)

See Also: SubStr, String

--------------------------------------------------------------------------------

SubStr = Func(
    String( String ),
    // String to get piece of
    Double( Start ),
    // Starting offset in String (0-based)
    Double( End )
    // Ending offset in String (inclusive)
) Returns( String )
Extracts a substring from Start to End (both inclusive, 0-based).

Example:
    SubStr( "hello~world", 0, 4 )   // returns "hello"
    SubStr( "hello~world", 6, 10 )  // returns "world"
    SubStr( "hello~world", 0, 5 )   // returns "hello~" (index 5 is '~')

See Also: StrPos, String

--------------------------------------------------------------------------------

StrReplace = Func(
    String( String ),
    // Original string (or RegExP pattern)
    String/RegExP( Search ),
    // String or regex pattern to find
    String( Replace ),
    // Replacement string
    Double( Flags )
    // REPL_GLOBAL to replace all occurrences (optional)
) Returns( String )
Replaces occurrences of Search in String with Replace.
Without REPL_GLOBAL, replaces only the first match.

Example:
    StrReplace( "aabaa", "a", "x", REPL_GLOBAL )   // "xxbxx"
    StrReplace( "abc123def", RegExP( "[0-9]+" ), "", REPL_GLOBAL )  // "abcdef"

See Also: RegExP, StrPos

--------------------------------------------------------------------------------

StrBegins = Func(
    String( String ),
    // String to test
    String( Prefix )
    // Prefix to check for
) Returns( Double )
Returns True if String starts with Prefix, False otherwise.

Example:
    StrBegins( "Exre [FAIL] breaks", "Exre [FAIL]" )   // True
    StrBegins( "hello world", "world" )                 // False

See Also: StrEnds, StrContains

--------------------------------------------------------------------------------

StrContains = Func(
    String( String ),
    // String to search in
    String( SubString )
    // String to search for
) Returns( Double )
Returns True if String contains SubString, False otherwise.
Case-insensitive (based on observed behavior).

Example:
    StrContains( "Process Monitor", "process" )   // True
    StrContains( "hello world", "xyz" )           // False

See Also: StrPos, StrBegins

--------------------------------------------------------------------------------

StrSplit = Func(
    String( String ),
    // String to split
    String( Delimiter ),
    // Delimiter to split on
    Double( IncludeEmpty )
    // Whether to include empty strings (optional)
) Returns( Array )
Splits String by Delimiter into an Array of substrings.

Example:
    StrSplit( "a.b.c", ".", False )   // [ "a", "b", "c" ]
    StrSplit( ".a.b", ".", False )    // [ "", "a", "b" ]

See Also: StrPos, SubStr

--------------------------------------------------------------------------------

RegExP = Func(
    String( Pattern )
    // Regular expression pattern string
) Returns( RegExP )
Compiles a regular expression pattern for use with StrReplace, RegMatch, etc.
Can use $~pattern~ syntax for inline regex literals.

Example:
    RE Digits = RegExP( "[0-9]+" );
    RE Digits = RegExP( $~[0-9]+~ );   // equivalent $~ syntax

See Also: RegMatch, StrReplace

--------------------------------------------------------------------------------

RegMatch = Func(
    RegExP( Pattern ),
    // Compiled regex pattern
    String( String )
    // String to match against
) Returns( Array )
Returns array of matches. Empty array if no match.
Size() of result can be used as a boolean test.

Example:
    Matches = RegMatch( RegExP( "[0-9]+" ), "abc123def" );
    // Matches = [ "123" ]
    If( Size( RegMatch( RegExP( "^[A-Z]" ), "Hello" ) ) )
        Print( "Starts with uppercase\n" );

See Also: RegExP, StrReplace

================================================================================

SLAM for slang
© Goldman Sachs
Generated by infra/apache/techdocs/generate-SLAM-docs~Host_1, run on d189512-014.dc.gs.com at Tue 10Feb26 09:09:04 pm (US/Eastern time).