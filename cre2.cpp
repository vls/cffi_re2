#include <re2/re2.h>
#include <string>
#include <iostream>
#include <vector>

using namespace std;

//The flag values have to match the corresponding Python definition
#define FLAG_UNICODE 1 // Always assumed
#define FLAG_CASE_INSENSITIVE 2
#define FLAG_MULTILINE 4
#define FLAG_DOTALL 8

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
     */
    int numGroups;
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
 * Create arg array from StringPiece array.
 * Caller must deallocate args with delete[]
 */
RE2::Arg* stringPiecesToArgs(re2::StringPiece* spc, int n) {
    RE2::Arg* args = new RE2::Arg[n];
    for (int i = 0; i < n; ++i) {
        args[i] = &spc[i];
    }
    return args;
}

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
    re2::RE2* RE2_new(const char* pattern, int flags) {
        re2::RE2::Options options;
        options.Copy(re2::RE2::Quiet);
        if(flags & FLAG_CASE_INSENSITIVE) {
            options.set_case_sensitive(false);
        }
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
                    for (int j = 0; j < mr.numGroups; ++j) {
                        if(mr.groupMatches[i][j] != NULL) {
                            delete[] mr.groupMatches[i][j];
                        }
                    }
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
        ret.numGroups = re_obj->NumberOfCapturingGroups();
        int pos = 0;
        int endidx = data.size();
        //Allocate temporary match array
        int nmatch = 1 + ret.numGroups;
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
            ret.groupMatches[i] = copyGroups(allMatches[i], nmatch);
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
        ret.numGroups = re_obj->NumberOfCapturingGroups();
        //Declare group target array
        re2::StringPiece* groups = new re2::StringPiece[ret.numGroups];
        RE2::Arg* args = stringPiecesToArgs(groups, ret.numGroups);
        //Perform either
        if(fullMatch) {
            ret.hasMatch = re2::RE2::FullMatchN(data, *re_obj, &args, ret.numGroups);
        } else {
            ret.hasMatch = re2::RE2::PartialMatchN(data, *re_obj, &args, ret.numGroups);
        }
        //Copy groups
        if(ret.hasMatch) {
            ret.groups = copyGroups(groups, ret.numGroups);
        } else {
            ret.groups = NULL;
        }
        //Cleanup
        delete[] groups;
        delete[] args;
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

}
