#pragma once
#include "Umfeld.h"

using namespace umfeld;

// Simple bouncing ball class

class Ball {
public:
    float x;
    float y;
    float speed;
    float gravity;
    float w;
    float life = 255;

    Ball(float tempX, float tempY, float tempW) {
        x       = tempX;
        y       = tempY;
        w       = tempW;
        speed   = 0;
        gravity = 0.1;
    }

    void move() {
        // Add gravity to speed
        speed = speed + gravity;
        // Add speed to y location
        y = y + speed;
        // If square reaches the bottom
        // Reverse speed
        if (y > height) {
            // Dampening
            speed = speed * -0.8;
            y     = height;
        }
    }

    bool finished() { //@diff(generic_type)
        // Balls fade out
        life--;
        if (life < 0) {
            return true;
        } else {
            return false;
        }
    }

    void display() {
        // Display the circle
        fill(0.f, life/255.f);
        //stroke(0,life);
        ellipse(x, y, w, w);
    }
};
