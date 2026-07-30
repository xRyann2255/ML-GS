
Input and Output




This chapter tells you how to obtain input and control output using Slang. It contains the following sections:

Obtaining Input
Outputting Information

Obtaining Input

Slang does not feature interactive command-line input mechanisms (like C's scanf). This is primarily because the language is optimized for retrieving information from SecDb objects and not for processing user-entered data. This does not mean that you can't accept user input, however. In fact, Slang features a collection of dialog box functions that you can use to obtain and evaluate user-entered information. This section discusses these dialog box functions. Chapter 11, "Working With SecDb Objects and Outside Information" explains how to interact with SecDb security objects and external data sources (such as Excel spreadsheets or text files).



Types of Dialog Boxes

Slang uses several different types of dialog boxes to obtain user input. The simplest of these asks a yes-or-no question and accepts a user's answer. Other types of dialogs allow users to select securities, or provide programmer-specified information. The rest of this section tells you how to create and read information from different types of dialog boxes.



Creating Yes-Or-No Dialogs

The easiest type of dialog box to create in Slang is one that presents a yes-or-no question. First, you call DialogAskYesNo, passing in a prompt and, if desired, a default value. Then, you analayze the returned value (1 for Yes and 0 for No). For example:



If( DialogAskYesNo( "Do you like carrots?", "Yes" ) == 1 )
{
    x = DialogAskYesNo( "True Statement? I love Brussels sprouts! ", False );
    If( x == 1 )
    {
        Print( "You love your veggies!" );
    }
    :
    {
        Print( "You only love some veggies." );
    };
}
:
{
    Print( "You're not a big veggie fan, eh?" );
};
This short program first draws a dialog box:




If the user enters No, then "You're not a big veggie fan, eh?" prints to screen. If the user enters Yes, then the following dialog is displayed:




If the user enters Yes again, then "You love your veggies!" prints to screen. If the user enters No, then "You only love some veggies" prints to screen.

This example demonstrates some of the important elements of Slang dialog box creation and control:


SecView automatically sizes dialog boxes to fit their contents.
When you create a dialog, you can assign it to a variable. This allows you to process and evaluate results.
Slang allows you to control the default values in dialog box fields.
You can include dialog box creation functions in control flow statements.
We will encounter additional features as we explore other types of dialog boxes that you can create using Slang.


Creating A Security Selector Dialog Box

If you want to ask a user to pick a certain type of financial object, you can do so with a special type of dialog box called a security selector. To create a security selector, you use the DialogAskSecPick function. This function has the following syntax:

     DialogAskSecPick( Prompt, Security Type, Default)

where Prompt is the field description to display in the dialog box, Security Type is the type of class that you want the user to select an instance of, and Default is the default value to display in the field.

For example, the following line of code creates a dialog in which a user can select an object of the type Bond Cash:

     DialogAskSecPick( "Pick a Cash Bond: ", "Bond Cash", "T USD 4.750 15Nov08 14 UNB0");

The dialog looks like this:




To view additional objects of the type Bond Cash, the user presses ?. When the user presses F9, the dialog returns the name of the selected object. You can use this object name to perform a number of operations. These operations are described in Chapter 11, "Working With SecDb Objects and Outside Information."



Creating a String Table Dialog Box

Another useful way to collect and work with user input is to construct a string table dialog box. This is simply a dialog box that displays a drop-down list of options from which a user can make a selection. The function that you use to create a string table dialog box is DialogAskStrTab. This function has the following syntax:

     DialogAskStrTab( Prompt, Options, Default)

where Prompt is the field description to display in the dialog box, Options is an array of strings from which the user can make a selection, and Default is the default value to display in the field (either a string listed in Options or a numeric index into the array).

For example, the following code creates a string table dialog box containing a list of items. When the user makes a selection, a string containing the selection is printed to the standard output area of SecView.



Choices =  ["Apple", "Banana", "Cherry", "Daffodil", "Endive",
            "Football", "Grape", "Halibut", "Iceberg Lettuce",
            "Jelly Beans", "Kumquat", "Lima Beans", "Melon",
            "Nuts", "Orange", "Popcorn", "Quince", "Radish",
            "Strawberry", "Trash", "Ugli Fruit", "Victrola",
            "Whiffleball", "X-Ray", "Yo-yo", "Zebra"];
a = DialogAskStrTab( "Make a selection: ", Choices, "Daffodil" );
Print("Your choice: ", Choices[a] );
The string table dialog constructed with the code above looks like this:






Creating Other Types of Dialog Boxes

Although DialogAskYesNo, DialogAskSecPick, and DialogAskStrTab are useful for constructing standard dialog boxes, you may also want to create custom dialog boxes. To do this, use Slang's Dialog function. The function has the following syntax:

     Dialog( Dialog, Inputs, Title, Subtitle, Defaults )

where the fields are defined as follows:


Dialog is an array of strings representing the fields in the dialog box
Inputs is a structure identifying any default values for the fields in Dialog
Title is an optional parameter specifying the window title for the dialog box
Subtitle is an optional parameter specifying the subtitle (bottom window title) of the dialog box
Defaults is an optional structure containing visual settings for the dialog box.
Although its signature is relatively simple, you can use Dialog to construct many different kinds of dialog boxes. This is largely because of dialog box constants and callback functions. A dialog box constant is a Slang constant that identifies a type of field, a window setting (such as foreground color), a message, or an action. A dialog box callback function is a method that you can use to act upon data that has already been entered in a dialog box. By combining these two constructs with the Dialog function, you can construct complex, interactive dialogs.
The following extended example demonstrates how to use the Dialog function.



An Extended Dialog Example

Suppose we want to create a dialog that asks a user to select a specific SecDb object and then displays the class type of that object. In order to construct this dialog, we need to do the following:


Create a framework for our dialog.

Customize the look-and-feel of the dialog.

Write a callback function that determines the class type for the selected security and then returns it to the dialog box.
The rest of this section describes these steps in detail.


Getting Started

Before we worry about determining the class type for a particular object, we should write some code that defines the structure of our dialog box:


Code Example 8-1 Framework code for our dialog box

Questions = TableInit(
                     [
                          [ "Type", "Component" ],
                          [ EI_SECPICK, "Object"],
                          [ EI_STRING, "Class Type"],
                      ]);
Inputs = Structure();
Inputs.Object = "Press ? for a list of objects";
Inputs.Class Type = "<No Object Selected>";
Dialog( Questions, Inputs);
After entering this code into the SecView Editor, press F9. You will see the following dialog box:




Notice that our call to Dialog references an array that we instantiated with TableInit. This array contains field types and names that SecView uses to construct our dialog box. Field types are listed as "Type" values in the TableInit array. All available field types are stored as constants that begin with the prefix EI (e.g., EI_DOUBLE and EI_ARRAY). Field names are listed as "Component" values in the TableInit array. They are strings used to identify the different fields in a dialog box.

In Code Example 8-1, our Type values are EI_SECPICK, which represents a field used to select SecDb objects (securities), and EI_STRING, which represents a field containing a string. Our Component values are Object and Class Type. You can specify additional fields within the TableInit array (we'll look at these in a moment), but at a minimum, you must include "Type" and "Component." You can look up EI constants from within the SecView Editor by pressing Alt+F4.



Customizing the Look-And-Feel of Our Dialog Box

Although SecView did a good job placing the fields and text within our dialog box, we want to customize some more visual elements, such as field size, color, spacing, etc. We can do this using a special TableInit array element and several optional TableInit fields.

In order to specify general properties of our dialog, we can add an element of the type EI_CONFIG to our TableInit array. This element must be the first entry in the array and must have the following format:

     [EI_CONFIG, "Config", "Extra", Config ]

where the Config value for "Extra" is a structure containing any of the components listed in Table 8-1. The values for these components are specified when you create the structure. For the most part, they are constants, though some components (such as DialogFKeys) take arrays or other non-constant values. For a sample Config structure, see Code Example 8-2.


Table 8-1 Components for the Config structure

Component Name	Formatting Information It Contains
Flags

General justification and return value settings. These are specified using constants that begin with EICF.

WindowFg/WindowBg

Foreground/Background color for the dialog box window.

WindowBorderFg/WindowBorderBg

Foreground/Background color for the dialog box window's border.

WindowTitleFg/WindowTitleBg

Foreground/Background color for the dialog box title.

WindowSubTitleFg/WindowSubTitleBg

Foreground/Background color for the dialog box subtitle.

TitleFg/TitleBg

Foreground/Background color for Title fields (those of the type EI_TITLE).

PromptFg/PromptBg

Foreground/Background color for prompts (either specified using the TableInit array's Prompt field or implicitly taken from the Component field if the Prompt field doesn't exist).

FieldFg/FieldBg

Foreground/Background color for fields. This is a generic component that you can override using CleanFg, EditedBg, etc.

CleanFg/CleanBg

Foreground/Background color for clean fields (those that have not yet been edited).

EditedFg/EditedBg

Foreground/Background color for edited fields.

UpdatedFg/UpdatedBg

Foreground/Background color for fields that have been updated by a function (rather than by editing).

DiddleCleanFg/DiddleCleanBg

Foreground/Background color for clean diddle fields.

DiddleEditedFg/DiddleEditedBg

Foreground/Background color for edited diddle fields.

DiddleErrorFg/DiddleErrorBg

Foreground/Background color for diddle errors.

DiddleUpdatedFg/DiddleUpdatedBg

Foreground/Background color for diddle fields that have been updated by a function (rather than by editing).

ReadOnlyFg/ReadOnlyBg

Foreground/Background color for read-only fields (those that can't be edited).

DialogCallBack

The name of a callback function to use for the dialog box

DialogFKeys

Function key assignments. These are listed in the hot key bar at the bottom of SecView. The value for this component is an array specifying a function key, a two-line label, and a Boolean value indicating whether the button is acceptable (1) or grayed-out (0). See Example: Dialog w/ Callbacks (in the Dev database) for sample usage.


In addition to Config components, we can include several additional fields in our TableInit array. These are described in Table 8-2. For sample usage, see Code Example 8-2.


Table 8-2 Additional fields for dialog box TableInit arrays

Field	What It Specifies
DataHeight

The height, in lines, of a prompt-field pair

DataWidth

The width, in characters, of a field.

DataX

The X-coordinate of a field.

DataY

The Y-coordinate of a field.

PromptX

The X-coordinate of a prompt.

PromptY

The Y-coordinate of a prompt.


The following code example shows how we can customize our dialog framework using a Config structure and additional TableInit array fields.


Code Example 8-2 Customized dialog box code

Config = Structure();
Config.Flags = "EICF_RIGHT_JUST + EICF_NO_DEFAULT";
Config.TitleFg = EIC_BRIGHT_GREEN;
Config.WindowTitleBg = EIC_RED;
Config.WindowBorderFg = EIC_YELLOW;
Config.CleanBg = EIC_BLACK;
DW = "DataWidth";
DX = "DataX";¦
PY = "PromptY";
Questions = TableInit(
[
    [ "Type",     "Component",  "Prompt",       DW, DX, PY,   "Extra"  ],
    [ EI_CONFIG,  "Config",            ,              ,   ,   , Config  ],
    [ EI_SECPICK, "Object",  "Choose a Security...", 35, 25, 0,  "Security"],
    [ EI_STRING,  "Class Type", "...See Its Type",   25, 25, 3,            ],
]);
Inputs = Structure();
Inputs.Object = "Press ? for a list of objects";
Inputs.Class Type = "<No Object Selected>";
a = Dialog(Questions, Inputs, "Example Dialog");
Now, if you press F9, you'll see a dialog box that looks like this:






Writing the Callback Function

Now that the dialog box is the way we want it, we're ready to write and integrate our callback function. This involves three steps:


Writing the function itself

Linking it to the dialog box

Ensuring that everything loads and operates properly
The callback function is simply an event handler that is called by the dialog box. Its source code is as follows:


MyCallBack = Func(
    Event,
    Info,
)
{
    If( Event == 0 )
    {
        Info.ReturnValue.Class Type = Security Type(Info.ReturnValue.Object);
        Return( EIA_NO_ACTION );
    }
    :
    {
        Return( EIA_DISABLE_EVENT );
    };
    Return( EIA_NO_ACTION );
};
This code reads each event that is sent to it and, if the event is of type 0 (user selection), then it updates the Class Type field to display the security type of the selected object. Otherwise, it ignores the event.

Next, we must link the callback to the dialog box. To do this, we modify the line of our TableInit array in which we define the Class Type field. The new line looks like this:

     [EI_STRING, "Class Type", ", "...See Its Type", 25, 25, 3, , "Callback", "@@MyCallBack(CallBackEvent, &CallBackInfo);"],

The "Callback"-"@@MyCallBack" pair identifies the callback function to send this field's messages to.

Finally, we should wrap the entire dialog creation routine into a function called Main to ensure that the callback function and dialog box variables are both loaded before they are accessed. To do this, we add Function = Main() to the top of our code and then enclose everything between Config = Structure() and a = Dialog(Questions, Inputs, "Example Dialog") in curly braces. To invoke the dialog, we add a call to @Main() (this should be the last line of the script). Our dialog is complete!

To view the complete source code for this extended example, open the SecView Editor and load Primer: Dialog With Callback from the Dev database.



Outputting Information

Slang features a rich set of functions that you can use to format and output information. This section describes those functions and explains how to use them. It covers the following topics:


Formatting Numeric Information
Printing to Screen
Printing to File
Printing to an Object

Formatting Numeric Information

Slang's Format function allows you to alter the appearance of your numeric data in several ways. You can specify width, decimal precision, and other stylistic options to create well-aligned reports and output. This section tells you how to do this.

The Format function converts numeric data into a string that is formatted for output. The function has the following signature:

     Format(NumericData, Width, Decimal, Flags)

where NumericData is the number to format, Width specifies the character width of the formatted string, Decimal indicates the number of digits after the decimal point (if applicable), and Flags are formatting flags. Table 8-3 lists all acceptable formatting flags.


Table 8-3 Flags for use with Format

Flag	What It Specifies
_Blank Zero

Display nothing if data is zero.

_Cipher

Display a single dash if data is zero.

_Commas

Add commas to delineate thousands, millions, etc.

_Concise

Trim leading and trailing spaces

_Pad Zeros

Add leading zeros.

_Parens

Put parentheses around negative numbers.

_Percent

Display data as a percentage (divide by 100).

_Plus Sign

Add a plus sign for positive numbers.

_Scale

Autoscale the number and add a suffix indicating the scale. Slang supplies one of the following suffixes: k (thousand), m (million), or b (billion).

_Trim Leading

Trim leading spaces.

_Full Precision

Display all significant digits.


In general, Format is used to convert doubles to formatted strings. You can, however, use it to convert decimals into integers, to truncate long numbers, etc. The following examples show two uses of Format.

Code Example 8-3 shows a basic usage in which a calculated double is converted to a truncated, formatted string. Notice that the value of the Format function's Width parameter is larger than the number of digits in the resulting number. This is because Width specifies the width of the output, including commas and decimal points. Thus 1000000 formatted with commas is nine characters wide (1,000,000).


Code Example 8-3 Basic usage of Format

Current Dollars = 1000000;
Future Dollars = Current Dollars;
APY = .0625;
Number of Years = 3;
For( i=1; i <= Number of Years; i++ )
{
    Future Dollars= Future Dollars * ( 1 + APY );
};
Future Dollars = Format( Future Dollars, 15, 2, _Commas + _Parens );
Print( Future Dollars );
Code Example 8-4 shows how you can use combine data type casting with Format to convert a randomly generated decimal number into an integer. First, we create a random number between 0 and 1 using Slang's Random function. Then, we format the number to a maximum width of three characters (with none after the decimal point) and cast it as a double. Finally, we perform a calculation using the random number and then print the result. If we did not cast the formatted random number to a double, we would not be able to use it as part of our calculations.


Code Example 8-4 Using data type casting with Format to convert a decimal into an integer

Random Number = 100*Random(3);
Random Number = Double(Format(Random Number, 3, 0));
Final Result = Random Number * 2;
Print(Final Result);


Printing to Screen

At some point, you will undoubtedly want to print information to screen. As you would expect, Slang provides several functions for doing this! The first is Print which simply prints information to screen. The second is Printf which, like its C counterpart, lets you specify formatting instructions for data that you print to screen. The following sections explain how to use both functions.



The Print Function

The easiest way to learn how to use the Print function is to examine a simple program. The following script is a variation of the famous C program "Hello, World." The script illustrates how to print to screen using the Print function (it also serves as a review of how to define functions).

The code for the script is as follows:



Print Text = Func(
    Text
)
{
   Print( Text, "\n" );
};
@Print Text( "Hello, World!" );
The first line of the script creates a new function called Print Text. This function takes one argument, which is assigned to the variable Text. The third line of the program defines the action that Print Text takes when it is called. This is simply to print the value of the passed-in argument followed by a new line. The fifth line calls Print Text, passing in a simple (and famous) string.

The important concepts in this example is that the Print function takes one or more arguments, separated by commas. Each of these arguments represents something to print to screen.

In the example above, Print(Text, "\n") first prints Text and then prints a newline character (represented by \n). If we wanted to print additional information on the new line, we would simply add it after \n. For instance, Print( Text, "\n", Text) would print the following to screen:

     Hello, World!

     Hello, World!



The Printf Function

Sometimes, you may want to format the information that you are going to print to screen. If the information is numeric, you can use the Format function. If it is a string, you can use the Printf function.

Printf takes one or more arguments. If you are only supplying one argument, then the function behaves like Print, outputting a quote-enclosed string to screen. If you include more than two arguments, then the first must be a formatting string that specifies how the output is to be displayed and the remaining arguments are the variable to print. The formatting string contains a combination of text and formatting codes. You must have one-to-one correspondance between your formatting codes and variables. All acceptable formatting strings are listed in Table 8-2.


Table 8-4 Formatting strings for Printf

Formatting Code	What It Means
%%

Print a percentage sign (%).

%d

Print a signed decimal number

%e

Print a double in the format n.ddddddE±xx

%f

Print a double in the format nnn.ddd

%g

Print a double in the format %e (if the exponent is less than -4) or %f (if the exponent is greater than or equal to -4)

%o

Print an unsigned octal number

%s

Print a string. You can specify a number of formatting modifiers for the %s code:

( or ):Put parentheses around negative numbers.

,: Add commas to delineate thousands, millions, etc.

@: Autoscale the number and add a suffix indicating the scale. Slang supplies one of the following suffixes: k (thousand), m (million), or b (billion)

&: Display data as a percentage (divide by 100).

^: Center the data

+: Add a plus sign for positive numbers

?: Display a single dash if data is 0

#: Show all trailing zeroes and leading spaces.

-: Left justify the data

>: Right justify the data (this is the default setting)

<: Trim leading spaces (even when # is specified)

_: Display nothing if data is 0.

For example, the following Printf call prints a double, d, as a left-justified number with commas separating the thousands, millions, and so on.

Printf("%-,s", d);

%v

Print something meaningful in the provided space. For example, Printf( "%20v", Curve ) prints a description of Curve that is no more than twenty characters long.

%x

Prints an unsigned hexadecimal number.


Code Example 8-5 shows how Printf statements work in Slang. The code assigns values to several variables and then prints two lines, each containing several formatting codes that are applied to the variables.


Code Example 8-5 Variable assignments and two sample Printf statements

d = 1200;
e = 455;
p = .12;
s1 = "of the students passed the test.";
s2 = "kinds of monkeys in the world.";
Printf("%<&s %<s\n", p, s1);
Printf("There are %d %s\n", d, s2);
Printf("%d in Hexadecimal is %x.\n", e, e);
The output from Code Example 8-5 looks like this:

     12% of the students passed the test.

     There are 1200 kinds of monkeys in the world.

     455 in Hexadecimal is 1c7.



The Sprint and Sprintf Functions

When you use Print or Printf, Slang outputs information to screen, but doesn't return any values. If you want to "print" values to string variables, you have to use the Sprint and Sprintf functions (the S stands for String). These functions behave exactly like Print and Printf except that they return strings rather than print to screen.

By storing formatting instructions in individual variables, Sprint and Sprintf allow you to output complex statements to screen easily. For example, the following code assigns three intricately formatted strings to variables and then prints those variables to screen (using additional formatting instructions).


Code Example 8-6 Example of Sprint and Sprintf

Benny = New("Structure");
Benny.age = 12;
Benny.height = 60;
Benny.weight = 105;
Benny.birthplace = "Ames, IA";
Chuck = New("Structure");
Chuck.age = 15;
Chuck.height = 68;
Chuck.weight = 135;
Chuck.birthplace = "Philadelphia, PA";
Debby = New("Structure");
Debby.age = 10;
Debby.height = 53;
Debby.weight = 95;
Debby.birthplace = "Schenectady, NY";
Convert Height = Func(
    Inches
)
{
    Feet = Inches/12;
    Feet = Format( Feet, 1, 1 );
    Inches = String( Mod( Inches, 12 ));
    Height = String( Feet + "'" + Inches + "\"" );
    Return( Height );
};
String =  Sprint(  "I have three children: Chuck, Benny, and Debby.\n");
String1 = Sprintf( "Chuck is %d. He was born in %s and is now %s tall.\n", Chuck.age,
                   Chuck.birthplace, @Convert Height(Chuck.height));
String2 = Sprintf( "Benny is %d. He's only %s, but weighs %d pounds.\n", Benny.age,
                   @Convert Height(Benny.height), Benny.weight);
String3 = Sprintf( "My youngest child is Debby. She's %d and was born in %s, our home
                    for the past 11 years.\n", Debby.age, Debby.birthplace);
Print(String, String1, String2, String3);
The output for Code Example 8-6 looks like this:

     I have three children: Chuck, Benny, and Debby.

     Chuck is 15. He was born in Philadelphia, PA and is now 5'8" tall.

     Benny is 12. He's only 5'0", but weighs 105 pounds.

     My youngest child is Debby. She's 10 and was born in Schenectady, NY, our home for the past 11 years.

A side-benefit of Sprintf is that you can use it to convert binary data types to strings. Simply call the function like this:

     Str = Sprintf( "%s", Binary Variable );



Printing to File

Sometimes, you may want to print to file. Depending on whether you also want to print to screen, there are two ways to do this in Slang. This section tells you about both of them.



PrintToFile

The PrintToFile function sends the output of a block of code to a file. The function has the following syntax:

     PrintToFile( FileName, AppendFlag ){ block };

where FileName is the name of the file that you want to print to and AppendFlag is a True/False value indicating whether to append the output from block to FileName. If you specify an existing file name and False for AppendFlag, Slang will overwrite the file. Make sure that you have set your parameters correctly before evaluating!

For example, the following code appends a status message to a file called output.log:



PrintToFile( "output.log", True )
{
    Print( "Function Executed Succesfully on ", Today(), "\n" );
};

