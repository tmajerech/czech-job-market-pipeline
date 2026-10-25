def extract_cs_text_sql(source_expression: str) -> str:
    """
    Some columns are described as text but contain an object with the key "cs" that holds the text.
    This function generates SQL to extract the "cs" text from such columns if needed.
    """
    return f"""
        CASE JSON_TYPE(TO_JSON({source_expression}))
            WHEN 'OBJECT'
                THEN JSON_EXTRACT_STRING(
                    TO_JSON({source_expression}),
                    '$.cs'
                )
            WHEN 'VARCHAR'
                THEN JSON_EXTRACT_STRING(
                    TO_JSON({source_expression}),
                    '$'
                )
            ELSE NULL
        END
    """.strip()
