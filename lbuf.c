#include <string.h>

#include <lua.h>
#include <lauxlib.h>

enum ctype {
    T_POINTER,
    T_FLOAT
};

static int lsizeof(lua_State *L) {
    lua_Integer type = luaL_checkinteger(L, 1);
    switch (type) {
    case T_POINTER: lua_pushinteger(L, sizeof(void*)); return 1;
    case T_FLOAT: lua_pushinteger(L, sizeof(float)); return 1;
    }
}

static int lnew(lua_State *L) {
    lua_Integer n = luaL_checkinteger(L, 1);
    lua_newuserdatauv(L, n, 0);
    return 1;
}

static int lget(lua_State *L) {
    void *p = lua_touserdata(L, 1);
    lua_Integer type = luaL_checkinteger(L, 2);
    lua_Integer i = luaL_checkinteger(L, 3);
    // void *ud;
    switch (type) {
    // case T_CUSTOM:
    //     ud = lua_newuserdatauv(L, size, 0);
    //     memcpy(ud, &((unsigned char *)p)[size*i], size);
    //     return 1;
    case T_POINTER: lua_pushlightuserdata(L, ((void **)p)[i]); return 1;
    case T_FLOAT: lua_pushnumber(L, (lua_Number)((float *)p)[i]); return 1;
    }
}

static int lslice(lua_State *L) {
    // todo: optional out table
    void *p = lua_touserdata(L, 1);
    lua_Integer type = luaL_checkinteger(L, 2);
    const lua_Integer i = luaL_checkinteger(L, 3);
    lua_Integer len = luaL_checkinteger(L, 4);
    lua_createtable(L, len, 0);
    switch (type) {
    case T_POINTER:
        for (lua_Integer j=0; len--; ++j) {
            lua_pushlightuserdata(L, ((void **)p)[i+j]);
            lua_seti(L, -2, j);
        }
    case T_FLOAT:
        for (lua_Integer j=0; len--; ++j) {
            lua_pushnumber(L, (lua_Number)((float *)p)[i+j]);
            lua_seti(L, -2, j);
        }
    }
    return 1;
}

static int lcopy(lua_State *L) {
    void *dst = lua_touserdata(L, 1);
    void *src = lua_touserdata(L, 2);
    lua_Integer n = luaL_checkinteger(L, 3);
    memcpy(dst, src, n);
    return 0;
}

static int loffset(lua_State *L) {
    unsigned char *p = lua_touserdata(L, 1);
    lua_Integer n = luaL_checkinteger(L, 2);
    lua_pushlightuserdata(L, &p[n]);
    return 1;
}

static luaL_Reg reg[] = {
    {"sizeof", lsizeof},
    {"new", lnew},
    {"get", lget},
    {"slice", lslice},
    {"copy", lcopy},
    {NULL, NULL},
};

int luaopen_lbuf(lua_State *L) {
    luaL_newlib(L, reg);
    return 1;
}
