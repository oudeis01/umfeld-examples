#pragma once
#include "Umfeld.h"

using namespace umfeld;

class Ring {
public:  
  float x, y; // X-coordinate, y-coordinate
  float diameter; // Diameter of the ring
  bool on = false; // Turns the display on and off //@diff(generic_type)

  void start(float xpos, float ypos) {
    x = xpos;
    y = ypos;
    on = true;
    diameter = 1;
  }
  
  void grow() {
    if (on == true) {
      diameter += 0.5;
      if (diameter > width*2) {
        diameter = 0.0;
      }
    }
  }
  
  void display() {
    if (on == true) {
      noFill();
      strokeWeight(4);
      stroke(.6f, .6f); //@diff(color_range)
      ellipse(x, y, diameter, diameter);
    }
  }
};
