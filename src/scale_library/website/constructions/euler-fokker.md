# Euler-Fokker genera

Take a list of numbers, say [3, 3, 5]. Form all products of any number of terms,

<pre class="narrow">
1, 3, 5, 3*3, 3*5, 3*3*5
</pre>

where 1 comes from 'the product of no terms'. Octave reduce to give

<pre class="narrow">
1, 3/2, 5/4, 9/8, 15/8, 45/32
</pre>

and sort to give the scale

<pre class="narrow">
1, 9/8, 5/4, 45/32, 3/2, 15/8
</pre>

with period 2/1.

The Euler-Fokker genus is made up of the [combination product
sets](/constructions/cps/) for each number of terms.

## Further reading

- [What is an Euler-Fokker genus?](https://www.huygens-fokker.org/microtonality/efg.html), Huygens-Fokker Foundation
