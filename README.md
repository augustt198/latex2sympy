# latex2sympy

latex2sympy parses LaTeX math expressions and converts it into the
equivalent SymPy form.

## Installation

[ANTLR](http://www.antlr.org/) is used to generate the parser:

```
$ antlr4 PS.g4 -o gen
```

## Usage

In Python 2.7:

```python
from process_latex import process_sympy

process_sympy("\\frac{d}{dx} x^{2}")
# => "diff(x**(2), x)"
```

## Examples

|LaTeX|Image|Generated SymPy|
|-----|-----|---------------|
|`x^{3}`|![](https://latex.codecogs.com/gif.latex?%5CLARGE%20x%5E%7B3%7D)| `x**3`|
|`\frac{d}{dx} |t|x`|![](https://latex.codecogs.com/gif.latex?%5CLARGE%20%5Cfrac%7Bd%7D%7Bdx%7D%20%7Ct%7Cx)|`Derivative(x*Abs(t), x)`|
|`\sum_{i = 1}^{n} i`|![](https://latex.codecogs.com/gif.latex?%5CLARGE%20%5Csum_%7Bi%20%3D%201%7D%5E%7Bn%7D%20i)|`Sum(i, (i, 1, n))`|
|`\int_{a}^{b} \frac{dt}{t}`|![](https://latex.codecogs.com/gif.latex?%5CLARGE%20%5Cint_%7Ba%7D%5E%7Bb%7D%20%5Cfrac%7Bdt%7D%7Bt%7D)|`Integral(1/t, (t, a, b))`|
|`(2x^3 - x + z)|_{x=3}`|![](https://latex.codecogs.com/gif.latex?%5CLARGE%20%282x%5E3%20-%20x%20&plus;%20z%29%7C_%7Bx%3D3%7D)|`z + 51`

## Contributing

Contributors are welcome! Feel free to open a pull request
or an issue.
