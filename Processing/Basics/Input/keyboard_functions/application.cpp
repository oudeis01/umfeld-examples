/**
 * Keyboard Functions 
 * by Martin Gomez 
 * 
 * Click on the window to give it focus and press the letter keys to type colors. 
 * The keyboard function keyPressed() is called whenever
 * a key is pressed. keyReleased() is another keyboard
 * function that is called when a key is released.
 * 
 * Original 'Color Typewriter' concept by John Maeda. 
 */
#include "Umfeld.h"
#include <glm/gtx/color_space.hpp>

using namespace umfeld;

int maxHeight    = 40;
int minHeight    = 20;
int letterHeight = maxHeight; // Height of the letters
int letterWidth  = 20;        // Width of the letter

int x = -letterWidth; // X position of the letters
int y = 0;            // Y position of the letters

bool newletter; //@diff(generic_type)

int numChars = 26;    // There are 26 characters in the alphabet
std::vector<uint32_t> colors(numChars); //@diff(std::vector, color_type)

void settings() {
    size(640, 360);
    
}

void setup() {
    noStroke();
    background(0.5f); //@diff(color_mode)
    // Set a hue value for each key
    for (int i = 0; i < numChars; i++) {
        // use GLM to convert HSB to RGB and store it
        // you can access the elements of glm::vec types 
        // with either .x .y .z .w or .r .g .b .a or [0], [1], [2], [3]
        glm::vec3 hsb;
        glm::vec3 rgb;
        // hsb.x is same as hsb.r or hsb[0]
        hsb.x = (float)i / (float)numChars;  // hue: 0-1
        hsb.y = 1.0f;  // saturation: full
        hsb.z = 1.0f;  // brightness: full
        rgb = glm::rgbColor(hsb);  // GLM expects hue in degrees
        colors[i] = color(rgb.r, rgb.g, rgb.b);
    }
}

void draw() {
    if(newletter == true) {
        // Draw the "letter"
        int y_pos;
        if (letterHeight == maxHeight) {
            y_pos = y;
            rect( x, y_pos, letterWidth, letterHeight );
        } else {
            y_pos = y + minHeight;
            rect( x, y_pos, letterWidth, letterHeight );
            fill(0.5f);
            rect( x, y_pos-minHeight, letterWidth, letterHeight );
        }
        newletter = false;
    }
}

void keyPressed() {
    // If the key is between 'A'(65) to 'Z' and 'a' to 'z'(122)
    if((key >= 'A' && key <= 'Z') || (key >= 'a' && key <= 'z')) {
        int keyIndex;
        if(key <= 'Z') {
            keyIndex = key-'A';
            letterHeight = maxHeight;
            fill_color(colors[keyIndex]);
        } else {
            keyIndex = key-'a';
            letterHeight = minHeight;
            fill_color(colors[keyIndex]);
        }
    } else {
        fill(0.0f);
        letterHeight = 10;
    }

    newletter = true;

    // Update the "letter" position
    x = ( x + letterWidth ); 

    // Wrap horizontally
    if (x > width - letterWidth) {
        x = 0;
        y+= maxHeight;
    }

    // Wrap vertically
    if( y > height - letterHeight) {
        y = 0;      // reset y to 0
    }
}
