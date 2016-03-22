#include <re2/re2.h>
#include <string>
#include <iostream>
#include <vector>

using namespace std;

static int maxMemoryBudget = 128 << 20; // 128 MiB

typedef struct {
    int start;
    int end;
} Range;

typedef struct {
    bool hasMatch;
    int numGroups;
    Range* ranges;
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
     * Match ranges
     */
    Range** ranges;
} REMultiMatchResult;

//clrsb: Number of leading bits equal to the sign bit (which we set to 0)
//clrsb(~b) - clrsb(0) + 8: Number of leading one bits in the byte b
#define count_leading_ones(b) __builtin_clrsb(~(char)(b))  - __builtin_clrsb(0) + 8

/**
 * Builds a lookup table (LUT) that allows mapping a cstring (memory) index
 * of a string to lookup (key: cstring coordinate) the character index in a UTF8 string.
 * 
 * Example: abcödef -> 0 1 2 3 3 4 5 6
 * @param s The string to map
 * @param len The length of s
 * @return a new[]-allocated int array of size len, containing the LUT
 */
int* buildUTF8IndexLUT(const char* s, size_t len) {
    int* lut = new int[len + 1];
    int sidx = 0; // Index in the LUT
    for(unsigned int i = 0 ; i < len ; i++) { // i = Current index in s
        if((s[i] & 0x80) == 0) { //Single-byte character
            lut[i] = sidx;
            sidx++;
        } else { //Start of multibyte. This branch handles the entire multibyte
            int multibyteSize = count_leading_ones(s[i]);
            //Set the next <multibyteSize> LUT entries to the current sidx
            for(unsigned int j = i; j < multibyteSize + i; j++) {
                lut[j] = sidx;
            }
            //Advance i to after the multibyte, but advance sidx by only 1
            // as the multibyte is treated as a single character
            i += multibyteSize - 1;
            sidx++;
        }
    }
    //Last entry is relevant when a group ends at the end of the string.
    // This behaviour leverages Python slicing automatically limiting the end index
    lut[len] = len;
    return lut;
}

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
        if(mr.ranges != NULL) {
            delete[] mr.ranges;
            mr.ranges = NULL;
        }
    }

    void FreeREMultiMatchResult(REMultiMatchResult mr) {
        if(mr.ranges != NULL) {
            for (int i = 0; i < mr.numMatches; ++i) {
                if(mr.ranges[i] != NULL) {
                    delete[] mr.ranges[i];
                    mr.ranges[i] = NULL;
                }
            }
            delete[] mr.ranges;
            mr.ranges = NULL;
        }
    }

    REMultiMatchResult FindAllMatches(re2::RE2* re_obj, const char* dataArg, int anchorArg, int startpos) {
        re2::StringPiece data(dataArg);
        if(anchorArg >= 2) {
            anchorArg = 0; //Should not happen
        }
        re2::RE2::Anchor anchor = anchorLUT[anchorArg];
        //Build UTF8 lookup table for string
        int* utf8LUT = buildUTF8IndexLUT(data.data(), data.size());
        //Initialize return arg
        REMultiMatchResult ret;
        ret.numMatches = 0;
        //Map anchor for easier Python iface
        int numGroups = re_obj->NumberOfCapturingGroups();
        ret.numElements = 1 + numGroups;
        int pos = startpos;
        int endidx = data.size();
        //We don't know the size of this in advance, so we'll need to allocate now
        re2::StringPiece* matchTmp = new re2::StringPiece[ret.numElements];
        vector<Range*> allRanges;
        /**
         * Iterate over all non-overlapping (!) matches
         */
        while(true) {
            //Perform match
            bool hasMatch = re_obj->Match(data, pos, endidx,
                 anchor, matchTmp, ret.numElements);
            if(!hasMatch) {
                break;
            }
            //Increment position pointer so we get the next hit
            // We are returning non-overlapping matches, so this is OK
            if(matchTmp[0].size() == 0) { //Zero-length match
                pos++;
            } else {
                pos = matchTmp[0].data() - dataArg + matchTmp[0].size() ;
            }
            //Copy range
            Range* rangeTmp = new Range[ret.numElements];
            for (int i = 0; i < ret.numElements; ++i) {
                if(matchTmp[i].data() == NULL) {
                    rangeTmp[i].start = -1;
                    rangeTmp[i].end = -1;
                    continue;
                }
                int rawStart = matchTmp[i].data() - dataArg;
                rangeTmp[i].start = utf8LUT[rawStart];
                rangeTmp[i].end = utf8LUT[rawStart + matchTmp[i].size()];
            }
            allRanges.push_back(rangeTmp);
        }
        //Compute final size
        ret.numMatches = allRanges.size();
        //Convert match vector to group vector (3D)
        ret.ranges = new Range*[allRanges.size()];
        for (size_t i = 0; i < allRanges.size(); ++i) {
            //Copy ranges
            ret.ranges[i] = new Range[ret.numElements];
            memcpy(ret.ranges[i], allRanges[i], sizeof(Range*) * ret.numElements);
        }
        //Cleanup
        delete[] utf8LUT;
        delete[] matchTmp;
        for (size_t i = 0; i < allRanges.size(); ++i) {
            if(allRanges[i] != NULL) {
                delete[] allRanges[i];
            }
        }
        return ret;
    }

    REMatchResult FindSingleMatch(re2::RE2* re_obj, const char* dataArg, bool startAnchored, int startpos) {
        re2::StringPiece data(dataArg);
        REMatchResult ret;
        ret.numGroups = re_obj->NumberOfCapturingGroups() + 1;
        //Declare group target array
        re2::StringPiece* groups = new re2::StringPiece[ret.numGroups]();
        //Build UTF8 lookup table for string
        int* utf8LUT = buildUTF8IndexLUT(data.data(), data.size());
        //Perform either
        re2::RE2::Anchor anchor = startAnchored ? re2::RE2::ANCHOR_START : re2::RE2::UNANCHORED;
        ret.hasMatch = re_obj->Match(data, startpos, data.size(),
                anchor, groups, ret.numGroups);
        //Copy groups
        if(ret.hasMatch) {
            //Copy ranges
            ret.ranges = new Range[ret.numGroups];
            for (int i = 0; i < ret.numGroups; ++i) {
                if(groups[i].data() == NULL) {
                    ret.ranges[i].start = -1;
                    ret.ranges[i].end = -1;
                    continue;
                }
                int rawStart = groups[i].data() - dataArg;
                ret.ranges[i].start = utf8LUT[rawStart];
                ret.ranges[i].end = utf8LUT[rawStart + groups[i].size()];
            }
        } else {
            ret.ranges = NULL;
        }
        //Cleanup
        delete[] groups;
        delete[] utf8LUT;
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
