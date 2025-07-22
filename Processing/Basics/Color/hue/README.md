# note

## missing feature

- [ ] needs hsb->rgb conversion support.

## subnote
- Currently, the `PVector` is implemented as the counterpart of the class in processing with the same name.
- But umfeld already includes the `glm` library internally.
- I suggest to replace `PVector` with `glm` completely, because `glm` provides much more math functions in terms of linear algebra.
- `fill()` and `fill_color()` sounds confusing, as they both fill the color of the shape. Maybe better to remove the `fill_color()` and create a new overriding of the `fill()` with different argument types such as `uint32_t`. Or, `fill_color()` can be renamed to `fill_i()`. I see there is already a `color_i()`, so in terms of consistency:)