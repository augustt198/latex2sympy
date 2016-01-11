# latex2sympy

latex2sympy parses LaTeX math expressions and converts it into the
equivalent SymPy form.

## Installation

[ANTLR](http://www.antlr.org/) is used to generate the parser:

```
$ antlr4 PS.g4 -o gen
```

## Usage

```python
from process_latex import process_sympy

process_sympy("\\frac{d}{dx} x^{2}")
# => "diff(x**(2), x)"
```

## Examples

|LaTeX|Generated SymPy|
|-----|---------------|
|`x^{3}`|`x**(3)`|
|`\frac{d}{dx} |t|x`|`diff(Abs(t)x, x)`|
|`\sum_{i = 1}^{n} i`|`summation(i, (i, 1, n))`|
|`\int_{a}^{b} (dt)/t`|`integrate((1) / t, (t, a, b))`|

## Contributing

Contributors are welcome! Feel free to open a pull request
or an issue.
