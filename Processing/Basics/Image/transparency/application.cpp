/**
 * Transparency. 
 * 
 * Move the pointer left and right across the image to change
 * its position. This program overlays one image over another 
 * by modifying the alpha value of the image with the tint() function. 
 */
#include "Umfeld.h"

using namespace umfeld;

PImage* img; //@diff(pointer)
float   offset = 0;
float   easing = 0.05;

void settings() {
    size(640, 360);
}

void setup() {
    img = loadImage("moonwalk.jpg"); // Load an image into the program
}

void draw() {
    image(img, 0, 0); // Display at full opacity
    float dx = (mouseX - img->width / 2) - offset; //@diff(pointer)
    offset += dx * easing;
    //FIXME: error: ‘tint’ was not declared in this scope; did you mean ‘uint’?
    // tint(255, 127); // Display at half opacity //unimplemented 
    image(img, offset, 0);
}
