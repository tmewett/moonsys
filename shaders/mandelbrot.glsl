#version 330
uniform vec2 resolution;
uniform vec2 offset;
uniform float time;
uniform float zoom;
const int maxIterations = 200;
const float escapeRadius = 100.0;
vec2 squareComplex(vec2 number){
	return vec2(
		pow(number.x,2)-pow(number.y,2),
		2*number.x*number.y
	);
}
vec3 getShade(float x) {
	// return 0.68 + 0.43 * cos(6.283*(x*0.05 + vec3(0.0, 0.288, 0.378)));
	return 0.5 + 0.4*cos( 3.0 + x*0.15 + vec3(0.0,0.6,1.0));
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
	if (ii < maxIterations) shade = getShade(float(ii));
    return vec4(shade, 1.0);
}
void main() {
	gl_FragColor = getColor(gl_FragCoord.xy), vec4(1.0);
}
