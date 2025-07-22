/**
 * Datatype Conversion. 
 * 
 * It is sometimes beneficial to convert a value from one type of 
 * data to another. Each of the conversion functions converts its parameter 
 * to an equivalent representation within its datatype. 
 * The conversion functions include int(), float(), char(), byte(), and others. 
 */
#include "Umfeld.h"

using namespace umfeld;

void settings() {
    size(640, 360);
}

void setup() {
    background(0.f);
    noStroke();
    PFont* font = loadFont("SourceCodePro-Regular.ttf", 24); //@diff(load_font)
    textFont(font);
}

void draw() {

    char  c; // Chars are used for storing alphanumeric symbols
    float f; // Floats are decimal numbers
    int   i; // Integers are values between 2,147,483,647 and -2147483648
    int8_t  b; // Bytes are values between -128 and 127 //@diff(generic_type)

    c = 'A';
    f = float(c);     // Sets f = 65.0
    i = int(f * 1.4); // Sets i to 91
    b = int8_t(c / 2);  // Sets b to 32

    //println(f);
    //println(i);
    //println(b);


/*
note:
- this example seems to not make sense in c++ if taken literally.
- adding int to a char array is a pointer operation, not a conversion.
- adding float to a char array is illegal.
- the example cannot be transcoded to support the original processing intention. requires a different approach.
- suggestion: create an original example that demonstrates the conversion of data types in a c++ way.
*/

    text(std::string("The value of variable c is ") + c, 50, 100);
    text("The value of variable f is " + std::to_string(f), 50, 150);
    text("The value of variable i is " + std::to_string(i), 50, 200);
    // text("The value of variable b is " + to_string(b), 50, 250);
    std::stringstream ss;
    ss << "The value of variable b is " << static_cast<int>(b);
    text(ss.str(), 50, 250);
}
