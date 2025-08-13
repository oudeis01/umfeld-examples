#pragma once
#include "Umfeld.h"
#include "PVector.h"

using namespace umfeld;

// A simple Particle class, renders the particle as an image

class Particle {
    PVector loc;
    PVector vel;
    PVector acc;
    float   lifespan;
    PImage* img;

public:
    Particle(PVector l, PImage* img_) {
        acc      = PVector(0, 0);
        float vx = randomGaussian() * 0.3;
        float vy = randomGaussian() * 0.3 - 1.0;
        vel      = PVector(vx, vy);
        loc      = l;
        lifespan = 100.0;
        img      = img_;
    }

    void run() {
        update();
        render();
    }

    // Method to apply a force vector to the Particle object
    // Note we are ignoring "mass" here
    void applyForce(PVector f) {
        acc.add(f);
    }

    // Method to update position
    void update() {
        vel.add(acc);
        loc.add(vel);
        lifespan -= 2.5;
        acc.mult(0); // clear Acceleration
    }

    // Method to display
    void render() {
        // imageMode(CENTER);
        // tint(255, lifespan);
        image(img, loc.x, loc.y);
        // Drawing a circle instead
        // fill(1.f,lifespan/255.f);
        // noStroke();
        // ellipse(loc.x,loc.y,img.width,img.height);
    }

    // Is the particle still useful?
    bool isDead() {
        if (lifespan <= 0.0) {
            return true;
        } else {
            return false;
        }
    }
};