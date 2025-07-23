/**
 * Create Image. 
 * 
 * The createImage() function provides a fresh buffer of pixels to play with.
 * This example creates an image gradient.
 */
#include "Umfeld.h"

using namespace umfeld;

PImage* img; //@diff(pointer)

void settings() {
    size(640, 360);
}

void setup() {
//   img = createImage(230, 230, ARGB); // unimplemented
  size_t pix_length = img->width * img->height * img->channels; //@diff(pointer)
  for(int i = 0; i < pix_length; i++) {
    float a = map(i, 0, pix_length, 255, 0); 
    img->pixels[i] = color(0, 153, 204, a);
  }
}

void draw() {
  background(0.f);
  image(img, 90, 80);
  image(img, mouseX-img->width/2, mouseY-img->height/2); //@diff(pointer)
}

/*
note:
- createImage() is not implemented.
- couldn't find any implementation to set the pixel format either. for pimage, nor pgraphics.
*/