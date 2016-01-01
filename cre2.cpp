#include <re2/re2.h>
#include <string>
#include <iostream>
#include <vector>

using namespace std;

static int maxMemoryBudget = 128 << 20; // 128 MiB

typedef struct {
    bool hasMatch;
    int numGroups;
    char** groups;
} REMatchResult;

/**
 * A multi match object which contains either:
 *  - A list of group matches (individual groups)
 *  - A list of regular matches (one group per match)
 */
typedef struct {
    /**
     * Length of either groupMatches or matches (depending on value of hasGroupMatches)
     */
    int numMatches;
    /**
     * If this result contains group matches, contains the number of groups,
     * i.e. the number of elements in every groupMatches element.
     * Undefined if groupMatches == NULL
     * At least one (in case )
     */
    int numElements;
    /**
     * Only filled if this result has group matches (else NULL)
     */
    char*** groupMatches;
} REMultiMatchResult;

/**
 * Lookup table that maps the Python anchor arg to actual anchors.
 */
static const re2::RE2::Anchor anchorLUT[] = {
    re2::RE2::UNANCHORED, re2::RE2::ANCHOR_BOTH, re2::RE2::ANCHOR_START};

/**
 * Copy a StringPiece array to a C string list,
 * each level of which is allocated using new[]
 */
char** copyGroups(const re2::StringPiece* groupsSrc, int numGroups) {
    char** groups = new char*[numGroups];
    for (int i = 0; i < numGroups; ++i) {
        char* group = new char[groupsSrc[i].size() + 1];
        group[groupsSrc[i].size()] = 0; //Insert C terminator
        //Copy actual string
        memcpy(group, groupsSrc[i].data(), groupsSrc[i].size());
        groups[i] = group;
    }
    return groups;
}

extern "C" {
    re2::RE2* RE2_new(const char* pattern, bool caseInsensitive) {
        re2::RE2::Options options;
        options.Copy(re2::RE2::Quiet);
        if(caseInsensitive) {
            options.set_case_sensitive(false);
        }
        options.set_max_mem(maxMemoryBudget);
        re2::RE2* ptr = new re2::RE2(pattern, options);
        return ptr;
    }

    int NumCapturingGroups(re2::RE2* re_obj) {
        return re_obj->NumberOfCapturingGroups();
    }

    void FreeREMatchResult(REMatchResult mr) {
        if(mr.groups != NULL) {
            for (int i = 0; i < mr.numGroups; ++i) {
                if(mr.groups[i] != NULL) {
                    delete[] mr.groups[i];
                }
            }
            delete[] mr.groups;
            mr.groups = NULL;
        }
    }

    void FreeREMultiMatchResult(REMultiMatchResult mr) {
        if(mr.groupMatches != NULL) {
            for (int i = 0; i < mr.numMatches; ++i) {
                if(mr.groupMatches[i] != NULL) {
                    for (int j = 0; j < mr.numElements; ++j) {
                        if(mr.groupMatches[i][j] != NULL) {
                            delete[] mr.groupMatches[i][j];
                        }
                    }
                    delete[] mr.groupMatches[i];
                    mr.groupMatches[i] = NULL;
                }
            }
            delete[] mr.groupMatches;
            mr.groupMatches = NULL;
        }
    }

    REMultiMatchResult FindAllMatches(re2::RE2* re_obj, const char* dataArg, int anchorArg) {
        re2::StringPiece data(dataArg);
        if(anchorArg >= 2) {
            anchorArg = 0; //Should not happen
        }
        re2::RE2::Anchor anchor = anchorLUT[anchorArg];
        //Initialize return arg
        REMultiMatchResult ret;
        ret.numMatches = 0;
        ret.groupMatches = NULL;
        //Map anchor for easier Python iface
        int numGroups = re_obj->NumberOfCapturingGroups();
        ret.numElements = max(1, numGroups);
        int pos = 0;
        int endidx = data.size();
        //Allocate temporary match array
        int nmatch = 1 + numGroups;
        //We don't know the size of this in advance, so we'll need to allocate now
        vector<re2::StringPiece*> allMatches;
        /**
         * Iterate over all non-overlapping (!) matches
         */
        while(true) {
            //Perform match
            re2::StringPiece* matchTmp = new re2::StringPiece[nmatch];
            bool hasMatch = re_obj->Match(data, pos, endidx,
                 anchor, matchTmp, nmatch);
            if(!hasMatch) {
                delete[] matchTmp;
                break;
            }
            //Add matchlist
            allMatches.push_back(matchTmp);
            //Increment position pointer so we get the next hit
            // We are returning non-overlapping matches, so this is OK
            if(matchTmp[0].size() == 0) {
                pos++;
            } else {
                pos += matchTmp[0].size();
            }
        }
        //Compute final size
        ret.numMatches = allMatches.size();
        //Convert match vector to group vector (3D)
        ret.groupMatches = new char**[allMatches.size()];
        for (size_t i = 0; i < allMatches.size(); ++i) {
            //re.findall behaviour: 0 groups -> 1 result,
            // 1 group -> 1 result, n > 1 groups -> n results
            if(numGroups >= 1) { //Do not emit full match
                ret.groupMatches[i] = copyGroups(allMatches[i] + 1, ret.numElements);
            } else { //Emit only full match
                ret.groupMatches[i] = copyGroups(allMatches[i], 1);
            }
        }
        //Cleanup
        for (size_t i = 0; i < allMatches.size(); ++i) {
            if(allMatches[i] != NULL) {
                delete[] allMatches[i];
            }
        }
        return ret;
    }

    REMatchResult FindSingleMatch(re2::RE2* re_obj, const char* dataArg, bool fullMatch) {
        re2::StringPiece data(dataArg);
        REMatchResult ret;
        ret.numGroups = re_obj->NumberOfCapturingGroups() + 1;
        //Declare group target array
        re2::StringPiece* groups = new re2::StringPiece[ret.numGroups]();
        //Perform either
        re2::RE2::Anchor anchor = fullMatch ? re2::RE2::ANCHOR_BOTH : re2::RE2::UNANCHORED;
        ret.hasMatch = re_obj->Match(data, 0, data.size(),
                anchor, groups, ret.numGroups);
        //Copy groups
        if(ret.hasMatch) {
            ret.groups = copyGroups(groups, ret.numGroups);
        } else {
            ret.groups = NULL;
        }
        //Cleanup
        delete[] groups;
        //Return
        return ret;
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

    void RE2_SetMaxMemory(int maxmem) {
        maxMemoryBudget = maxmem;
    }

}
