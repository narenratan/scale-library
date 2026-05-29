# Combination product sets

Given the list of numbers [1, 3, 5, 7], take all products of two numbers,

<pre class="narrow">
1*3, 1*5, 1*7, 3*5, 3*7, 5*7
</pre>

Now pick one of these products as the root, say 3. Divide each number by the
root

<pre class="narrow">
1, 5/3, 7/3, 5, 7, 35/3
</pre>

and reduce within one octave

<pre class="narrow">
1, 5/3, 7/6, 5/4, 7/4, 35/24
</pre>

These ratios 1, 7/6, 5/4, 35/24, 5/3, 7/4 form the 1-3-5-7 hexany.

Choosing different products as root gives different modes of the same scale.

In general, given a list of n numbers, taking products of k numbers gives a CPS
written nCk. The scale gets a name based on its number of tones:

| Name          | Tones |
|---------------|-------|
| monany        | 1     |
| dyany         | 2     |
| triany        | 3     |
| tetrany       | 4     |
| pentany       | 5     |
| hexany        | 6     |
| dekany        | 10    |
| pentadekany   | 15    |
| eikosany      | 20    |

## Further reading

- [The Hexany, the Eikosany, and the Other Combination Product Sets](https://www.anaphoria.com/wilsoncps.html), The Wilson Archives
