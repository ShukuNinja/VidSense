def region_grower(array):
    if len(array) == 0:
        return []

    final = []
    region = [array[0]]

    i = 1

    while i < len(array):
        prev = array[i-1]
        if prev + 1 == array[i]:
            region.append(array[i])
        else:
            final.append(region)
            region = [array[i]]
        
        i += 1

    final.append(region)

    return final


def build_context(retrieved_chunks):
    evidence = {"regions": [], "sources": []}
    chunk_ids = []

    for chunk in retrieved_chunks:
        chunk_ids.append(chunk["chunk_id"])

    chunk_lookup = {chunk["chunk_id"]: chunk for chunk in retrieved_chunks}

    chunk_ids.sort()

    regions = region_grower(chunk_ids)

    while region_id < len(regions):

        current_region = regions [region_id]

        region_dict = {"region_id": None, "chunks": []}

        j = 0

        while j < len(current_region):
            chunk_id = current_region[j]

            if chunk_id in chunk_lookup:
                chunk = dict(chunk_lookup[chunk_id])
                region_dict["chunks"].append(chunk)
                evidence["sources"].append(chunk)

            j += 1

        evidence["regions"].append(region_dict)
        region_id += 1

    evidence["sources"] = retrieved_chunks

    return evidence

    