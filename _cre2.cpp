

#include <re2/re2.h>
#include <string>
#include <iostream>

using namespace std;

extern "C" {
    re2::RE2* RE2_new(const char* pattern) {
        re2::RE2* ptr = new re2::RE2(pattern, re2::RE2::Quiet);
        return ptr;
    }

    bool PartialMatch(re2::RE2* re_obj, const char* data) {

        return re2::RE2::PartialMatch(data, *re_obj);
    }

    void RE2_delete(re2::RE2* re_obj) {
        delete re_obj;
    }

    string* RE2_GlobalReplace(re2::RE2* re_obj, const char* str, const char* rewrite) {
        string* ptr_s = new string(str);
        re2::StringPiece sp(rewrite);

        re2::RE2::GlobalReplace(ptr_s, *re_obj, sp);
        return ptr_s;

    }

    const char* get_c_str(string* ptr_str) {
        if(ptr_str == NULL) {
            return NULL;
        }
        return ptr_str->c_str();
    }

    void RE2_delete_string_ptr(string* ptr) {
        delete ptr;
    }

    const char* get_error_msg(re2::RE2* re_obj) {
        if(!re_obj) {
            return "";
        }
        string* ptr_s = (string*) &(re_obj->error());
        return get_c_str(ptr_s);
    }
    
    bool ok(re2::RE2* re_obj) {
        if(!re_obj) {
            return false;
        }
        return re_obj->ok();
    }

}
