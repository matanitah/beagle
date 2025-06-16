import textdistance
from typing import Set, Any, Dict, List, Tuple, Hashable
class Benchmarker:
    def get_jw_distance(self, string1: str, string2: str) -> float:
        """
        Calculate the Jaro-Winkler distance between two strings.

        The Jaro-Winkler distance is a measure of similarity between two strings.
        The score is normalized such that 0 equates to no similarity and
        1 is an exact match.
        """
        # Call the jaro_winkler function from the textdistance library.
        return textdistance.jaro_winkler(string1, string2)

    def rowsim(self, setL: Set, setR: Set) -> float:
        """
        Calculate the similarity between two sets using Jaccard index formula.
        """
        return len(setL.intersection(setR)) / len(setL.union(setR))


    def floatify(self, v: Any) -> Any:
        """
        Attempts to convert a value to a float if it is a string and represents a
        number, or recursively apply the conversion to elements within a list or dict.
        """
        if isinstance(v, str):
            return v
        try:
            f = float(v)
            return f
        except:
            pass
        if isinstance(v, list):
            return [self.floatify(x) for x in v]
        if isinstance(v, dict):
            return {k: self.floatify(u) for k, u in v.items()}
        return v 
    
    def make_hashable(self, v: Any) -> Hashable:
        """
        Convert a value to a hashable type (needed for set operations).
        """
        float_v = self.floatify(v)
        if not isinstance(float_v, Hashable):
            return str(float_v)
        else:
            return float_v


    def make_alignment(self, dictL: List[Dict], dictR: List[Dict]) -> Tuple[List[Set], List[Set]]:
        """
        Align rows from two lists of dictionaries based on their similarity.
        """
        swap = len(dictL) > len(dictR)

        # Forming set views from the list of dictionaries.
        setViewsL = [{self.make_hashable(v) for k, v in row.items()} for row in dictL]
        setViewsR = [{self.make_hashable(v) for k, v in row.items()} for row in dictR]
        if swap:
            setViewsL, setViewsR = setViewsR, setViewsL

        for i in range(len(setViewsL)):
            max_sim = -1
            max_j = -1
            for j in range(i, len(setViewsR)):
                sim = self.rowsim(setViewsL[i], setViewsR[j])
                if sim > max_sim:
                    max_j = j
                    max_sim = sim
            tmp = setViewsR[i]
            setViewsR[i] = setViewsR[max_j]
            setViewsR[max_j] = tmp
        if swap:
            setViewsL, setViewsR = setViewsR, setViewsL
        return setViewsL, setViewsR


    def df_sim(self, dictL: List[Dict], dictR: List[Dict], list_view: bool) -> float:
        """
        Calculate the data frame similarity based on either the original row order or an alignment.
        """
        if list_view:
            # Original row order for lists of dictionaries
            view_L = [row.values() for row in dictL]
            view_R = [row.values() for row in dictR]
        else:
            view_L, view_R = self.make_alignment(dictL, dictR)

        totalSetL = set()
        for i, s in enumerate(view_L):
            for elem in s:
                totalSetL.add((i, self.make_hashable(elem)))
        totalSetR = set()
        for i, s in enumerate(view_R):
            for elem in s:
                totalSetR.add((i, self.make_hashable(elem)))
        intersection = totalSetL.intersection(totalSetR)
        union = totalSetL.union(totalSetR)

        if len(union) == 0 and len(intersection) == 0:
            return 1.0
        elif len(union) == 0:
            return 0.0

        return len(intersection) / len(union)


    def df_sim_pair(self, pair_L, pair_R):
        """
        Compute the Jaccard similarity of two data frames (lists of dictionaries),
        taking into account the order of rows if indicated by the involved Cypher queries.
        """
        cypher_L, dict_L = pair_L
        cypher_R, dict_R = pair_R

        return self.df_sim(dict_L, dict_R, "order by" in f"{cypher_L} {cypher_R}".lower()) 