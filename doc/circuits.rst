================
Circuit Analysis
================


Introduction
============

Lcapy can only analyse linear time invariant (LTI) circuits, this
includes both passive and active circuits.  Time invariance means that
the circuit parameters cannot change with time; i.e., capacitors
cannot change value with time.  It also means that the circuit
configuration cannot change with time, i.e., contain switches
(although switching problems can be analysed, see
:ref:`switching-analysis`).

Linearity means that superposition applies---if you double the voltage
of a source, the current (anywhere in the circuit) due to that source
will also double.  This restriction rules out components such as
diodes and transistors that have a non-linear relationship between
current and voltage (except in circumstances where the relationship
can be approximated as linear around some constant value---small
signal analysis).  Linearity also rules out capacitors where the
capacitance varies with voltage and inductors with hysteresis.



Networks and netlists
=====================

Lcapy circuits can be created using a netlist specification (see
:ref:`netlists`) or by combinations of components (see
:ref:`networks`).  For example, here are two ways to create the same
circuit:

   >>> cct1 = (Vstep(10) + R(1)) | C(2)

   >>> cct2 = Circuit()
   >>> cct2.add('V1 1 0 step 10')
   >>> cct2.add('R1 1 2 1')
   >>> cct2.add('C1 2 0 2')

The two approaches have many attributes and methods in common.  For example,

   >>> cct1.is_causal
   True
   >>> cct2.is_causal
   True
   >>> cct1.is_dc
   False
   >>> cct2.is_dc
   False

However, there are subtle differences.  For example,

   >>> cct1.Voc.laplace()
      5   
   ──────
    2   s
   s  + ─
        2

   >>> cct2.Voc(2, 0).laplace()
      5   
   ──────
    2   s
   s  + ─
        2

Notice, the second example requires specific nodes to determine the
open-circuit voltage across.  The advantage of the netlist approach is
that component names can be used , for example,

   >>> cct2.V1.V.laplace()
      5   
   ──────
    2   s
   s  + ─
        2



Linear circuit analysis
=======================

There is no universal analytical technique to determine the voltages
and currents in an LTI circuit.  Instead there are a number of methods
that all try to side step having to solve simultaneous
integro-differential equations.  These methods include DC analysis, AC
analysis, and Laplace analysis.  Lcapy uses all three and the
principle of superposition.  Superposition allows a circuit to be
analysed by considering the effect of each independent current and
voltage source in isolation and summing the results.

Lcapy's algorithm for solving a circuit is:
1. If a capacitor or inductor is found to have initial conditions, then the
circuit is analysed as an initial value problem using Laplace methods.
In this case, the sources are ignored for :math:`t<0` and the result
is ony known for :math:`t\ge 0`.
2. If there are no capacitors and inductors and if none of the independent sources are specified in the s-domain, then time-domain analysis is performed.
3. Finally, Lcapy tries to decompose the sources into DC, AC, transient, and noise components.  The circuit is analysed for each source category using the appropriate transform domain (phasors for AC, s-domain for transients) and the results are added.

If there are multiple noise sources, these are considered independently since they are assumed to be uncorrelated.  
   

DC analysis
-----------

The simplest special case is for a DC independent source.  DC is an
idealised concept---it impossible to generate---but is a good
approximation for very slowly changing sources.  With a DC independent
source the dependent sources are also DC and thus no voltages or
currents change.  Thus capacitors can be replaced with open-circuits
and inductors can be replaced with short-circuits.  Note, each node
must have a DC path to ground otherwise the circuit cannot be solved
(for example, when capacitors are in series).


AC analysis
-----------

AC, like DC, is an idealised concept.  It allows circuits to be
analysed using phasors and impedances.  The use of impedances avoids
solving integro-differential equations in the time domain.


Laplace analysis
----------------

The response due to a transient excitation from an independent source
can be analysed using Laplace analysis.  Since the unilateral
transform is not unique (it ignores the circuit behaviour for :math:`t
< 0`), the response can only be determined for :math:`t \ge 0`.

If the independent sources are known to be causal (a causal signal is
zero for :math:`t < 0` analogous to a causal impulse response) and the
initial conditions (i.e., the voltages across capacitors and currents
through inductors) are zero, then the response is 0 for :math:`t < 0`.
Thus in this case, the response can be specified for all :math:`t`.

The response due to a general non-causal excitation is hard to
determine using Laplace analysis.  One strategy is to use circuit
analysis techniques to determine the response for :math:`t < 0`,
compute the pre-initial conditions, and then use Laplace analysis to
determine the response for :math:`t \ge 0`.  Note, the pre-initial
conditions at :math:`t = 0_{-}` are required.  These differ from the
initial conditions at :math:`t = 0` whenever a Dirac delta (or its
derivative) excitation is considered.  Determining the initial
conditions is not straightforward for arbitrary excitations and at the
moment Lcapy expects you to do this!

The use of pre-initial conditions also allows switching circuits to be
considered (see :ref:`switching-analysis`).  In this case the
independent sources are ignored for :math:`t < 0` and the result is
only known for :math:`t \ge 0`.

Note if any of the pre-initial conditions are non-zero and the
independent sources are causal then either we have an initial value
problem or a mistake has been made.  Lcapy assumes that if any of the
inductors and capacitors have explicit initial conditions, then the
circuit is to be analysed as an initial value problem with the
independent sources ignored for :math:`t \ge 0`.  In this case a DC
source is not DC since it is considered to switch on at :math:`t = 0`.


.. _switching-analysis:

Switching analysis
------------------

Whenever a circuit has a switch it is time variant.  The opening or
closing of switch changes the circuit and can produce transients.
While a switch violates the LTI requirements for linear circuit
analysis, the circuit prior to the switch changing can be analysed and
Vnoiused to determine the initial conditions for the circuit after the
switched changed.  Lcapy requires that you do this!  The independent
sources are ignored for :math:`t < 0` and the result is only known for
:math:`t \ge 0`.


Noise analysis
--------------

Each noise source is assigned a noise indentifier (nid).  Noise
expressions with different nids are assumed to be independent and thus
represent different noise realisations.

Lcapy analyses the circuit for each noise realisation independently
and stores the result for each realisation separately.  For example,
   >>> a = Circuit()
   >>> a.add('Vn1 1 0 noise 3')
   >>> a.add('Vn2 2 1 noise 4')
   >>> a[2].V
   {n1: 3, n2: 4}
   >>> a[1].V
   {n1: 3}
   >>> a[2].V - a[1].V
   {n1: 0, n2: 4}
   >>> a[2].V.n
   5

Notice that the `.n` attribute returns the total noise found by adding each
noise component in quadrature since they have different nids and are thus
independent.

Each resistor in a circuit can be converted into a series combination
of an ideal resistor and a noise voltage source using the
`noise_model` method.
