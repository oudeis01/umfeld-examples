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

uint32_t hsb_to_rgb_packed(const float h, const float s, const float b, const float a = 1.0f) {
    const float H = std::clamp(h, 0.0f, 1.0f);
    const float S = std::clamp(s, 0.0f, 1.0f);
    const float V = std::clamp(b, 0.0f, 1.0f);
    const float A = std::clamp(a, 0.0f, 1.0f);

    float r = 0, g = 0, bl = 0;
    float hh = H * 6.0f;         // hue slice
    int   i  = static_cast<int>(hh);
    float f  = hh - i;
    float p  = V * (1.0f - S);
    float q  = V * (1.0f - S * f);
    float t  = V * (1.0f - S * (1.0f - f));

    switch (i % 6) {
        case 0: r = V;  g = t;  bl = p; break;
        case 1: r = q;  g = V;  bl = p; break;
        case 2: r = p;  g = V;  bl = t; break;
        case 3: r = p;  g = q;  bl = V; break;
        case 4: r = t;  g = p;  bl = V; break;
        case 5: r = V;  g = p;  bl = q; break;
    }
    return (static_cast<uint32_t>(A * 255) << 24) |
           (static_cast<uint32_t>(bl * 255) << 16) |
           (static_cast<uint32_t>(g  * 255) <<  8) |
            static_cast<uint32_t>(r  * 255);
}

void fill_with_hsb_to_rgb(float h, float s, float b, float a = 1.0f) {
    fill_color(hsb_to_rgb_packed(h, s, b, a));
}
void fill_with_hsb_to_rgb_uint(uint32_t color) {
    float r, g, b, a;
    color_unpack(color, r, g, b, a);
    fill_with_hsb_to_rgb(r, g, b, a);
}

void settings() {
    size(640, 360);
}

void setup() {
    noStroke();
    background(.5f); //@diff(color_range)
    // Set a hue value for each key
    for (int i = 0; i < numChars; i++) {
        colors[i] = color((float)i/(float)numChars, (float)numChars/(float)numChars, (float)numChars/(float)numChars); //@diff(color_range, color_type)
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
            fill_with_hsb_to_rgb_uint(float(numChars/2)/255.f);
            rect( x, y_pos-minHeight, letterWidth, letterHeight );
        }
        newletter = false;
    }
}

void keyPressed() { //FIXME: key is case insensitive?
    // If the key is between 'A'(65) to 'Z' and 'a' to 'z'(122)
    if((key >= 'A' && key <= 'Z') || (key >= 'a' && key <= 'z')) {
        int keyIndex;
        if(key <= 'Z') {
        keyIndex = key-'A';
        letterHeight = maxHeight;
        fill_with_hsb_to_rgb_uint(colors[keyIndex]);
        } else {
        keyIndex = key-'a';
        letterHeight = minHeight;
        fill_with_hsb_to_rgb_uint(colors[keyIndex]);
        }
    } else {
        fill(0.f);
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
