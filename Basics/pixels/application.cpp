#include "Umfeld.h"

using namespace umfeld;

PImage* myImage;

void settings() {
    size(1024, 768);
}

void setup() {
    myImage = loadImage("drip.png");
}

void draw() {
    const int halfImage = width * height / 2;
    image(myImage, 0, 0);

    loadPixels();
    for (int i = 0; i < halfImage; i++) {
        pixels[i + halfImage] = pixels[i];
    }
    updatePixels();

    noStroke();
    fill(1.0f);
    debug_text("FPS: " + to_string(frameRate), 10, 20);
}
