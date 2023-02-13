#version 330
uniform vec2 resolution;
uniform vec2 offset;
uniform float zoom;
const int maxIterations = 50;
vec2 squareComplex(vec2 number){
	return vec2(
		pow(number.x,2)-pow(number.y,2),
		2*number.x*number.y
	);
}
int iterations(vec2 p) {
	return maxIterations;
}
void main() {
    vec2 p = (-resolution.xy + 2.0*(gl_FragCoord.xy))/resolution.y;
	p = p/zoom - 2.0 * offset / resolution.y;
	vec2 z = vec2(0,0);
	int i = 0;
	for (; i < maxIterations; i++){
		z = vec2(z.x*z.x - z.y*z.y, 2*z.x*z.y) + p;
		if (length(z)>2) break;
	}
    float intensity = 0.0;
    if (i < maxIterations) {
        intensity = float(i) / maxIterations;
    }
    gl_FragColor = vec4(vec3(1.0) * intensity, 1.0);
}
