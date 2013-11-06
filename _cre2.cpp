

#include <re2/re2.h>
#include <string>

using namespace std;

extern "C" {
    re2::RE2* RE2_new(const char* pattern) {
        return new re2::RE2(pattern);
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
    

}
