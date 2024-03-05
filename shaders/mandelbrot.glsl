#version 330
uniform vec2 resolution;
uniform vec2 offset;
uniform float time;
uniform float zoom;
const int maxIterations = 200;
const float escapeRadius = 100.0;
vec3 oklab_mix( vec3 colA, vec3 colB, float h )
{
    const mat3 kCONEtoLMS = mat3(
         0.4121656120,  0.2118591070,  0.0883097947,
         0.5362752080,  0.6807189584,  0.2818474174,
         0.0514575653,  0.1074065790,  0.6302613616);
    const mat3 kLMStoCONE = mat3(
         4.0767245293, -1.2681437731, -0.0041119885,
        -3.3072168827,  2.6093323231, -0.7034763098,
         0.2307590544, -0.3411344290,  1.7068625689);

    // rgb to cone (arg of pow can't be negative)
    vec3 lmsA = pow( kCONEtoLMS*colA, vec3(1.0/3.0) );
    vec3 lmsB = pow( kCONEtoLMS*colB, vec3(1.0/3.0) );
    // lerp
    vec3 lms = mix( lmsA, lmsB, h );
    // gain in the middle (no oaklab anymore, but looks better?)
    lms *= 1.0+0.2*h*(1.0-h);
    // cone to rgb
    return kLMStoCONE*(lms*lms*lms);
}
vec3 getShadeL(float t) {
    t = pow(t, 0.8);
	return vec3(pow(t, 1.5), pow(t, 1.2), pow(t, 0.5) - 0.05);
}
vec3 getShadeH(float t) {
    t = pow(t, 1.2);
	return vec3(t/6., t/3., pow(t, 0.8));
}
// x is 0 at set boundary, 1 at infinity.
vec3 getShade(float x) {
    // Shift gradient so it becomes closer to boundary over time, where we will be zoomed.
	x = pow(x, 1. / (1. + time/60.));
	return oklab_mix(getShadeL(time/30.0), getShadeH(time/30.0), x);
}
vec4 getColor(vec2 p) {
    p = (-resolution.xy + 2.0*(p.xy))/resolution.y;
	p = p/zoom + 2.0 * offset / resolution.y;
	vec2 z = vec2(0,0);
	int i = 0;
	float maxIterations = 2*time;
	for (; i < int(floor(maxIterations)); i++){
		if (length(z)>escapeRadius) break;
		z = vec2(z.x*z.x - z.y*z.y, 2*z.x*z.y) + p;
	}
	float ii = i - log2(log(length(z))/log(escapeRadius));
	vec3 shade = vec3(0.0);
	if (ii < maxIterations) shade = getShade(float(maxIterations - ii) / maxIterations);
    return vec4(shade, 1.0);
}
void main() {
    vec4 color = vec4(0.);
    for (int i=0; i<2; i++) for (int j=0; j<2; j++) {
        vec2 o = vec2(float(i), float(j)) / 2.0 - 0.5;
        color += getColor(gl_FragCoord.xy + o);
    }
	gl_FragColor = color / 4.;
}
