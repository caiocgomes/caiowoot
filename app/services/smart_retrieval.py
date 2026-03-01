import logging

from app.database import get_chroma_collection, get_db

logger = logging.getLogger(__name__)


def index_edit_pair(
    edit_pair_id: int,
    situation_summary: str,
    was_edited: bool = False,
    validated: bool = False,
    rejected: bool = False,
    approach_selected: str = "",
):
    collection = get_chroma_collection()
    collection.upsert(
        ids=[str(edit_pair_id)],
        documents=[situation_summary],
        metadatas=[{
            "edit_pair_id": edit_pair_id,
            "was_edited": was_edited,
            "validated": validated,
            "rejected": rejected,
            "approach_selected": approach_selected,
        }],
    )


def update_metadata(edit_pair_id: int, **kwargs):
    collection = get_chroma_collection()
    existing = collection.get(ids=[str(edit_pair_id)])
    if not existing["ids"]:
        return
    metadata = existing["metadatas"][0]
    metadata.update(kwargs)
    collection.update(ids=[str(edit_pair_id)], metadatas=[metadata])


def retrieve_similar(situation_summary: str, k: int = 5) -> list[int]:
    collection = get_chroma_collection()

    if collection.count() == 0:
        return []

    # First try validated (non-rejected) pairs
    validated_ids = []
    try:
        n_validated = min(k, collection.count())
        results = collection.query(
            query_texts=[situation_summary],
            n_results=n_validated,
            where={"$and": [{"validated": True}, {"rejected": False}]},
        )
        validated_ids = [int(id_) for id_ in results["ids"][0]]
    except Exception:
        # No validated pairs or filter error
        pass

    if len(validated_ids) >= k:
        return validated_ids[:k]

    # Fill remaining from all non-rejected pairs
    remaining = k - len(validated_ids)
    try:
        n_all = min(k + len(validated_ids), collection.count())
        results = collection.query(
            query_texts=[situation_summary],
            n_results=n_all,
            where={"rejected": False},
        )
        all_ids = [int(id_) for id_ in results["ids"][0]]
        for id_ in all_ids:
            if id_ not in validated_ids and remaining > 0:
                validated_ids.append(id_)
                remaining -= 1
    except Exception:
        pass

    return validated_ids[:k]


async def rebuild_index():
    collection = get_chroma_collection()

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT id, situation_summary, was_edited, validated, rejected FROM edit_pairs WHERE situation_summary IS NOT NULL"
        )
        pairs = await rows.fetchall()

        for pair in pairs:
            collection.upsert(
                ids=[str(pair["id"])],
                documents=[pair["situation_summary"]],
                metadatas=[{
                    "edit_pair_id": pair["id"],
                    "was_edited": bool(pair["was_edited"]),
                    "validated": bool(pair["validated"]),
                    "rejected": bool(pair["rejected"]),
                    "approach_selected": "",
                }],
            )

        logger.info("Rebuilt ChromaDB index with %d edit pairs", len(pairs))
    finally:
        await db.close()
