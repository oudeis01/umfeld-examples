/**
 * Background Image. 
 * 
 * This example presents the fastest way to load a background image
 * into Processing. To load an image as the background, it must be
 * the same width and height as the program.
 */

#include "Umfeld.h"

using namespace umfeld;

PImage* bg; //@diff(pointer)
int     y;

void settings() {
    size(640, 360);
}

void setup() {
    // The background image must be the same size as the parameters
    // into the size() method. In this program, the size of the image
    // is 640 x 360 pixels.
    bg = loadImage("moonwalk.jpg");
}

void draw() {
    background(bg);

    stroke(1.f, 0.8f, 0); //@diff(color_range)
    line(0, y, width, y);

    y++;
    if (y > height) {
        y = 0;
    }
}
