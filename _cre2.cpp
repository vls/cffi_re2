

#include <re2/re2.h>

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
    

}
